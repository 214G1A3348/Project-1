"""
ML risk-scoring service.
Loads the trained RandomForest model and returns a risk score for a return request.
"""
import joblib
import numpy as np
from utils.logger import get_logger
from config import MODEL_PATH, SCALER_PATH

logger = get_logger(__name__)

_model = None
_scaler = None


def _load_model():
    global _model, _scaler
    if _model is None:
        _model = joblib.load(MODEL_PATH)
        _scaler = joblib.load(SCALER_PATH)
        logger.info("ML model and scaler loaded successfully.")


def predict_risk(features: dict) -> dict:
    """
    Accepts a dict of return features and returns:
    {
        "risk_score": float,   # 0-1 probability of high risk
        "risk_level": str,     # LOW | MEDIUM | HIGH
        "feature_importances": dict
    }
    """
    _load_model()

    feature_order = [
        "total_orders_count",
        "total_returns_count",
        "account_age",
        "average_return_time",
        "fraud_history_flag"
    ]

    try:
        X = np.array([[features.get(f, 0) for f in feature_order]], dtype=float)
        X_scaled = _scaler.transform(X)
        risk_score = float(_model.predict_proba(X_scaled)[0][1])

        if risk_score >= 0.90:
            risk_level = "HIGH"
        elif risk_score >= 0.50:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        importances = dict(zip(feature_order, _model.feature_importances_))

        return {
            "risk_score": round(risk_score, 4),
            "risk_level": risk_level,
            "feature_importances": {k: round(v, 4) for k, v in importances.items()},
            "status": "ok",
        }

    except Exception as e:
        logger.exception("ML prediction failed.")
        return {
            "risk_score": 0.5,
            "risk_level": "MEDIUM",
            "feature_importances": {},
            "status": "error",
            "error_message": str(e),
        }
