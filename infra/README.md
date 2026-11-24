# Infrastructure

## Local

The Dockerfiles build the local backend and kiosk frontend. From the repository root:

```bash
docker compose up --build
```

- `backend.Dockerfile` — the FastAPI app (uvicorn on :8000).
- `frontend.Dockerfile` — the Svelte kiosk built and served by nginx on :80.

## AWS capture stack (issue #14)

[`template.yaml`](template.yaml) is an AWS SAM template deployed to `us-east-2`. It runs the
capture API and the #12 annotator; recognition (#21) and retrain (#16) add resources later.

| Resource | What it is |
| --- | --- |
| `CaptureBucket` | One S3 bucket for `raw/`, `captures/`, `datasets/`, `models/`. Public access blocked; CORS allows POST from the console origins. `DeletionPolicy: Retain`, so `sam delete` never deletes captures or models. |
| `CaptureApiFunction` | The FastAPI app on Lambda (`api.Dockerfile`, default dependencies only) behind an HTTP API, through Lambda Web Adapter so the app runs unchanged. `/recognize` answers 503 here — recognition runs on the GPU box (#21). |
| `HttpApi` | API Gateway HTTP API proxying every path to the capture API. CORS is handled by the app (`AVC_CORS_ORIGINS`), not the gateway. |
| `AnnotatorFunction` | The #12 image (`annotator.Dockerfile`), 3008 MB memory (this account's Lambda cap; 10 GB where the account allows), 15 minute timeout, triggered by S3 `ObjectCreated` on the `raw/` prefix only. It writes to `captures/`, so it cannot trigger itself. |
| `AnnotatorInvokePermission` | Lets S3 invoke the annotator. |

Roles are least-privilege: the API reads the bucket, writes `captures/*` and `catalog.json`, and
presigns `raw/*` (`s3:PutObject`); the annotator reads `raw/` and `captures/` and writes `captures/`.

The bucket name is a template parameter (`BucketName`) so the S3 trigger and the API's
`AVC_STORE` can reference it without a CloudFormation dependency cycle. Set a globally unique
value in [`../samconfig.toml`](../samconfig.toml).

### Deploy and teardown

From the repository root, with the SAM CLI and Docker installed:

```bash
sam build                          # builds the container images (needs Docker)
sam deploy                         # pushes the images to ECR and creates the stack
sam delete                         # removes everything except the bucket
```

Stack outputs: `ApiUrl` (set `frontend/.env` `VITE_CAPTURE_API_URL` to it) and `BucketName`.

The capture API stores to `AVC_STORE` (`s3://<bucket>` in the stack). Locally it defaults to the
directory `ml/data/pipeline`, so the API runs with no AWS account; `POST /captures` then points
the browser at a local upload route instead of a presigned S3 POST.

### Images

- `api.Dockerfile` — capture API Lambda image: uv default dependencies, the app, the shared
  `ml/scripts/store.py`, and Lambda Web Adapter (uvicorn on :8080, readiness `/health`).
- `annotator.Dockerfile` — annotator Lambda image (see [`../ml/README.md`](../ml/README.md)).