"""
FastAPI main application — Enterprise AI Return Validation System.
"""
import asyncio
import sys
import os

# Ensure root is on path so services/utils resolve correctly
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from services.hive_service import analyze_image
from services.ml_service import predict_risk
from services.decision_engine import decide, map_image_status
from utils.logger import get_logger
import config

logger = get_logger("main")

app = FastAPI(
    title="Enterprise AI Return Validation System",
    version="1.0.0",
    description="Production-grade return fraud detection with Hive AI + ML",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# ── Request / Response Schemas ────────────────────────────────────────────────

class ValidationResponse(BaseModel):
    image_status: str
    confidence: Optional[float]
    fake_score: Optional[float]
    real_score: Optional[float]
    risk_level: str
    risk_score: float
    action: str
    reason: str
    severity: str
    feature_importances: dict
    hive_status: str
    hive_error: Optional[str]


# ── Demo customers dataset ────────────────────────────────────────────────────
DEMO_CUSTOMERS = [
    {
        "id": "CUST-001",
        "name": "Rahul Sharma",
        "product": "Sony WH-1000XM5 Headphones",
        "total_orders_count": 42,
        "total_returns_count": 2,
        "account_age": 720,
        "average_return_time": 8,
        "fraud_history_flag": 0,
        "return_type": "return",
    },
    {
        "id": "CUST-002",
        "name": "Priya Mehta",
        "product": "Apple iPhone 15 Pro",
        "total_orders_count": 18,
        "total_returns_count": 11,
        "account_age": 45,
        "average_return_time": 2,
        "fraud_history_flag": 1,
        "return_type": "returnless",
    },
    {
        "id": "CUST-003",
        "name": "Amit Verma",
        "product": "Lakme Absolute Foundation",
        "total_orders_count": 27,
        "total_returns_count": 5,
        "account_age": 300,
        "average_return_time": 12,
        "fraud_history_flag": 0,
        "return_type": "return",
    },
    {
        "id": "CUST-004",
        "name": "Sneha Patel",
        "product": "Samsung 65\" 4K QLED TV",
        "total_orders_count": 9,
        "total_returns_count": 7,
        "account_age": 15,
        "average_return_time": 1,
        "fraud_history_flag": 1,
        "return_type": "returnless",
    },
    {
        "id": "CUST-005",
        "name": "Vikram Nair",
        "product": "Puma Running Shoes",
        "total_orders_count": 65,
        "total_returns_count": 3,
        "account_age": 1200,
        "average_return_time": 20,
        "fraud_history_flag": 0,
        "return_type": "return",
    },
]


@app.get("/api/demo-customers")
async def get_demo_customers():
    """Return the list of demo customers for the UI."""
    return DEMO_CUSTOMERS


# ── Core validation endpoint ──────────────────────────────────────────────────

@app.post("/api/validate", response_model=ValidationResponse)
async def validate_return(
    image: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    total_orders_count: int = Form(20),
    total_returns_count: int = Form(2),
    account_age: int = Form(365),
    average_return_time: int = Form(10),
    fraud_history_flag: int = Form(0),
    return_type: str = Form("return"),
):
    logger.info(f"Validate request: orders={total_orders_count}, returns={total_returns_count}, fraud_flag={fraud_history_flag}")

    image_bytes = await image.read() if image else None
    filename = image.filename if image else "image.jpg"

    ml_features = {
        "total_orders_count": total_orders_count,
        "total_returns_count": total_returns_count,
        "account_age": account_age,
        "average_return_time": average_return_time,
        "fraud_history_flag": fraud_history_flag,
    }

    # ── Parallel execution ────────────────────────────────────────────────────
    hive_task = analyze_image(image_bytes=image_bytes, image_url=image_url, filename=filename)
    ml_task   = asyncio.get_event_loop().run_in_executor(None, predict_risk, ml_features)

    hive_result, ml_result = await asyncio.gather(hive_task, ml_task)

    # ── Map image status ──────────────────────────────────────────────────────
    image_status = map_image_status(hive_result["is_deepfake"], hive_result["confidence"])

    # ── Decision engine ───────────────────────────────────────────────────────
    decision = decide(
        image_status=image_status,
        image_confidence=hive_result["confidence"] or 0.5,
        risk_level=ml_result["risk_level"],
        risk_score=ml_result["risk_score"],
        return_type=return_type,
    )

    return ValidationResponse(
        image_status=image_status,
        confidence=hive_result["confidence"],
        fake_score=hive_result["fake_score"],
        real_score=hive_result["real_score"],
        risk_level=ml_result["risk_level"],
        risk_score=ml_result["risk_score"],
        action=decision["action"],
        reason=decision["reason"],
        severity=decision["severity"],
        feature_importances=ml_result["feature_importances"],
        hive_status=hive_result["status"],
        hive_error=hive_result["error_message"],
    )


# ── Demo quick-validate (no image, uses stored customer features) ─────────────
@app.post("/api/validate-demo/{customer_id}")
async def validate_demo_customer(customer_id: str, image_url: Optional[str] = None):
    customer = next((c for c in DEMO_CUSTOMERS if c["id"] == customer_id), None)
    if not customer:
        raise HTTPException(status_code=404, detail="Demo customer not found")

    ml_features = {k: v for k, v in customer.items() if k not in ("id", "name", "product", "return_type")}
    return_type = customer["return_type"]

    hive_task = analyze_image(image_url=image_url) if image_url else _mock_hive()
    ml_task   = asyncio.get_event_loop().run_in_executor(None, predict_risk, ml_features)

    hive_result, ml_result = await asyncio.gather(hive_task, ml_task)

    image_status = map_image_status(hive_result["is_deepfake"], hive_result["confidence"])
    decision = decide(
        image_status=image_status,
        image_confidence=hive_result["confidence"] or 0.5,
        risk_level=ml_result["risk_level"],
        risk_score=ml_result["risk_score"],
        return_type=return_type,
    )

    return {
        "customer": customer,
        "image_status": image_status,
        "confidence": hive_result["confidence"],
        "fake_score": hive_result["fake_score"],
        "real_score": hive_result["real_score"],
        "risk_level": ml_result["risk_level"],
        "risk_score": ml_result["risk_score"],
        "action": decision["action"],
        "reason": decision["reason"],
        "severity": decision["severity"],
        "feature_importances": ml_result["feature_importances"],
        "hive_status": hive_result["status"],
        "hive_error": hive_result["error_message"],
    }


async def _mock_hive() -> dict:
    """Used when no image URL is supplied in demo mode."""
    return {
        "is_deepfake": None,
        "confidence": None,
        "fake_score": None,
        "real_score": None,
        "raw_classes": [],
        "status": "error",
        "error_message": "No image provided — demo mode without image",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=config.DEBUG)
