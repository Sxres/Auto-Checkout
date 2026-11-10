# Vision Self-Checkout
Barcode-free self-checkout kiosk for grocery stores, powered by computer vision.

## Overview

Shoppers place items on the checkout surface, a camera identifies each one,
and the kiosk builds the order and total automatically. No barcode scanning.
Inspired by the Uniqlo and H&M self-checkout kiosks.

## Features

- Real-time detection and recognition of grocery items
- Automatic cart building and price calculation
- Touchscreen kiosk interface
- (add more as you build them)

## How It Works

1. Camera captures the checkout surface
2. YOLO26 detects and classifies items
3. Backend matches detections to products and prices
4. Frontend shows the cart for review
5. Shopper confirms and pays

## Tech Stack

| Layer    | Tech                          |
|----------|-------------------------------|
| Frontend | (React / Next.js / etc.)      |
| Backend  | (FastAPI / Flask / Node, etc.)|
| ML       | YOLO26, PyTorch               |
| Cloud    | (AWS / GCP / Azure)           |

## Getting Started

### Prerequisites

- Python 3.x
- Node.js x.x
- (GPU / CUDA if needed)

### Installation

```bash
git clone https://github.com/<org>/vision-checkout.git
cd vision-checkout

cp .env.example .env   # then fill in your values

# backend
cd backend
pip install -r requirements.txt

# frontend
cd ../frontend
npm install
```

### Running Locally

```bash
# backend
cd backend && uvicorn app.main:app --reload

# frontend
cd frontend && npm run dev
```

## Project Structure

See [docs/architecture.md](docs/architecture.md) for details.

## Model and Data

- **Model:** YOLO26 fine-tuned on (dataset name)
- **Classes:** (number and examples)
- **Dataset:** (source, size, license)
- **Weights:** (download link or script)

## Design

Figma prototype: (link)

## Roadmap

- [x] Figma prototype
- [ ] Baseline detection model
- [ ] Backend API
- [ ] Frontend kiosk UI
- [ ] Cloud deployment
- [ ] Payment integration

## Team

- Name, role
- Name, role

## License

Distributed under the (MIT) License. See `LICENSE` for details.

## Acknowledgments

- Ultralytics YOLO
- (datasets, libraries, tutorials)
