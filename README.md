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
| Cloud | GCP (planned) |

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

### With Python and Node.js

Use Python 3.12 and Node.js 22.12 or later. From the repository root, start the API in one terminal.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
cd backend
python -m uvicorn app.main:app --reload
```

Start the kiosk in a second terminal.

```bash
cd frontend
npm ci
npm run dev
```

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
python -m ruff check .
python -m pytest
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
