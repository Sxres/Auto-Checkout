# Annotator Lambda (issue #12): S3 raw/{capture_id}/source.<ext> -> captures/{capture_id}/.
# Build from the repo root:  docker build -f infra/annotator.Dockerfile -t annotator .
# Run locally through the base image's runtime interface emulator: see ml/README.md.
FROM public.ecr.aws/lambda/python:3.12 AS base

# CPU PyTorch; ultralytics pulls opencv-python, which needs GUI libraries Lambda lacks, so swap in
# the headless build of the same version. boto3 comes with the base image.
RUN pip install --no-cache-dir torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir ultralytics==8.4.211 \
    && v=$(pip show opencv-python | sed -n 's/^Version: //p') \
    && pip uninstall -y opencv-python \
    && pip install --no-cache-dir "opencv-python-headless==$v"

# Lambda's filesystem is read-only outside /tmp
ENV YOLO_CONFIG_DIR=/tmp/Ultralytics
COPY ml/scripts/annotate.py ${LAMBDA_TASK_ROOT}/

# Save the shape prompts into the weights here, so the final image ships 71 MB of weights
# and not YOLOE's 600 MB text encoder
FROM base AS weights
WORKDIR ${LAMBDA_TASK_ROOT}
# Only this stage needs git and CLIP (ultralytics installs it from GitHub to encode the prompts)
RUN microdnf install -y git \
    && pip install --no-cache-dir git+https://github.com/ultralytics/CLIP.git
RUN mkdir /build && ANNOTATOR_WEIGHTS=/build/yoloe-11l-shapes.pt python -c "import annotate; annotate.model()"

FROM base
ARG ANNOTATOR_IMAGE=annotator:local
ENV YOLO_OFFLINE=1 \
    ANNOTATOR_WEIGHTS=${LAMBDA_TASK_ROOT}/yoloe-11l-shapes.pt \
    ANNOTATOR_IMAGE=${ANNOTATOR_IMAGE}
COPY --from=weights /build/yoloe-11l-shapes.pt ${LAMBDA_TASK_ROOT}/
CMD ["annotate.handler"]
