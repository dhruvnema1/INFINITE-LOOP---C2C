from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from model_service import PatternModel
from scoring import analyze_page
from comparison import compare_product

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model.joblib"

app = FastAPI(title="Dark Pattern Detector API", version="1.0.0")

# Only the browser extension should call this local service.
# CORS is limited to the Chrome extension origin plus localhost development.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^chrome-extension://.*$",
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

model_service = PatternModel(MODEL_PATH)


class ScanRequest(BaseModel):
    url: str = Field(default="", max_length=4096)
    title: str = Field(default="", max_length=1000)
    text: str = Field(default="", max_length=120000)
    prices: list[dict[str, Any]] = Field(default_factory=list)
    dom_signals: dict[str, Any] = Field(default_factory=dict)
    product_name: str = Field(default="", max_length=1000)
    brand: str = Field(default="", max_length=300)
    identifiers: list[str] = Field(default_factory=list, max_length=20)


@app.get("/health")
def health():
    return {
        "ok": True,
        "model_loaded": model_service.loaded,
        "classes": model_service.classes,
    }


@app.post("/scan")
async def scan(request: ScanRequest):
    if not model_service.loaded:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI model is not trained. Run "
                "python training/train_model.py --data <dataset.csv> "
                "--output backend/model.joblib"
            ),
        )

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="No visible page text was extracted.")

    ml = model_service.predict(request.text)
    current_price = request.dom_signals.get("current_price")
    old_price = request.dom_signals.get("old_price")
    comparison = compare_product(
        product_name=request.product_name or request.title,
        brand=request.brand,
        current_url=request.url,
        current_price=current_price,
        claimed_old_price=old_price,
    )
    return analyze_page(
        url=request.url,
        title=request.title,
        text=request.text,
        prices=request.prices,
        dom_signals=request.dom_signals,
        ml_predictions=ml,
        comparison=comparison,
    )
