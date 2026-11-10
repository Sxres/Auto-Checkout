# Checkout Architecture

The starter scaffold serves the kiosk screen and the API health endpoint. The following sections describe the planned checkout, management, and model training flows.

## Checkout

1. The kiosk camera captures items on the checkout surface. The kiosk associates each request with a checkout session.
2. The application API calls YOLO26 inference. Inference returns a class label, confidence score, and bounding box for each detection.
3. The application maps confident detections to catalog products. The product catalog supplies product IDs and prices. Cart logic tracks items across frames to avoid adding the same item repeatedly.
4. The kiosk displays the updated cart and totals. The shopper reviews the order before confirming checkout.
5. Low-confidence detections enter the staff review queue for correction. Checkout and inference events supply operational metrics.

## Service Boundaries

| Area | Responsibility |
| --- | --- |
| `frontend/` | Camera preview, cart review, shopper actions, and manager views |
| `backend/app/` | Checkout sessions, cart rules, catalog lookup, pricing, and manager API |
| `backend/inference/` | YOLO26 model loading and frame prediction |
| `ml/` | Dataset preparation, training configurations, evaluation, and experiment notes |
| `infra/` | Local containers and future deployment configuration |

The product database is the source of truth for price and product metadata. It also stores checkout and review records, including references to images in object storage. The kiosk and manager views access this data through the application API. A lookup cache can be introduced alongside catalog update invalidation if lookup latency warrants it.

## Manager Console

The design covers checkout and item metrics, review of uncertain detections, catalog updates, retraining, monitoring, and settings. Monitoring tracks camera availability, checkout failures, API latency and errors, inference latency, and the low-confidence rate.

## Model Feedback Loop

Dataset preparation joins reviewed labels with stored images and writes versioned training and evaluation splits. Training and evaluation run separately from checkout requests. A reviewed model version can be promoted to the inference service after evaluation against a held-out dataset.

The [design directory](design/README.md) is the home for prototype references.
