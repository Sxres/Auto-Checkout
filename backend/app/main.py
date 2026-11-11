from fastapi import FastAPI

app = FastAPI(title="Auto Vision Checkout API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
