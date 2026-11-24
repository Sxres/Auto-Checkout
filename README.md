# Auto Vision Checkout

Barcode-free self-checkout kiosk for grocery stores, powered by computer vision.

## Overview

Shoppers place items on the checkout surface. The planned system uses YOLO26 to recognize items and builds a cart from the product catalog. Staff use the manager console to review uncertain detections, manage the catalog, and monitor the kiosk.

The starter scaffold runs a Svelte kiosk screen and a FastAPI health endpoint. See the [planned architecture](docs/architecture.md) and the [design directory](docs/design/README.md).

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | Svelte and Vite |
| Backend | FastAPI |
| ML | YOLO26 and PyTorch (planned) |
| Cloud | AWS — SAM, Lambda, S3 (capture API + annotator) |

## Run Locally

Clone the repository and copy the example environment file.

```bash
git clone https://github.com/Sxres/Auto-Checkout.git
cd Auto-Checkout
cp .env.example .env
```

### With Docker Compose

```bash
docker compose up --build
```

The kiosk opens at [localhost:5173](http://localhost:5173). The API health check is at [localhost:8000/health](http://localhost:8000/health). Adjust the ports in the local environment file if needed.

### With uv and Node.js

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Node.js 22.12 or later. From the repository root, start the API in one terminal. The Python version is pinned in `.python-version`; uv fetches it automatically if it is not already installed.

```bash
uv sync
cd backend
uv run uvicorn app.main:app --reload
```

`uv sync` creates the virtual environment and installs everything from `uv.lock`. Add dependencies with `uv add <package>` (or `uv add --dev <package>` for development tools).

Start the kiosk in a second terminal.

```bash
cd frontend
npm ci
npm run dev
```

## Deploy to AWS

The capture API and annotator deploy with AWS SAM from [`infra/template.yaml`](infra/template.yaml)
into `us-east-2` (issue #14). You need the [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html),
Docker, and an account whose deploying user can use CloudFormation, IAM, S3, Lambda, ECR, API
Gateway, and CloudWatch Logs.

1. Set a globally unique `BucketName` in [`samconfig.toml`](samconfig.toml).
2. Build the container images (needs Docker), then deploy — SAM pushes them to ECR:

   ```bash
   sam build
   sam deploy
   ```

3. Point the console at the stack. From the stack outputs, set `frontend/.env`:

   ```bash
   VITE_CAPTURE_API_URL=<ApiUrl output>
   ```

4. Import the 4 starter products into the bucket (the upload triggers the annotator):

   ```bash
   uv run python ml/scripts/import_fooddata.py fooddata s3://<BucketName output>
   ```

`/recognize` answers 503 on the capture API — recognition runs on the GPU box (#21). Teardown
removes everything except the bucket (captures and models are retained):

```bash
sam delete
```

See [`infra/README.md`](infra/README.md) for the stack's resources and [`ml/README.md`](ml/README.md)
for the capture contract and the annotation pipeline.

## Project Structure

| Path | Purpose |
| --- | --- |
| `docs/` | Architecture and a directory for design references |
| `frontend/` | Svelte kiosk UI |
| `backend/app/` | FastAPI routes and checkout business logic |
| `backend/inference/` | YOLO26 model loading and prediction |
| `backend/tests/` | API and business logic tests |
| `ml/` | Training configurations, notebooks, and scripts |
| `ml/data/` | Local dataset files, ignored by Git |
| `infra/` | Dockerfiles and deployment configuration |

## Checks

After installing the backend and frontend dependencies, run these commands from the repository root.

```bash
cd backend
uv run ruff check .
uv run python -m pytest
cd ../frontend
npm run build
```

## Roadmap

- [x] Figma prototype
- [x] Runnable repository scaffold
- [ ] Baseline detection model and dataset
- [ ] Cart, catalog, and checkout API
- [ ] Customer and manager workflows
- [ ] Cloud deployment
- [ ] Payment integration

## License

See the [MIT license](LICENSE).

## Acknowledgments

- Ultralytics YOLO
