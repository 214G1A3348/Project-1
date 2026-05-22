"""
Central configuration for the Enterprise AI Return Validation System.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Hive AI ──────────────────────────────────────────────────────────────────
HIVE_API_KEY: str = os.getenv("HIVE_API_KEY", "tXl1otC+chmyAdEhKldlgA==")
HIVE_API_URL: str = "https://api.thehive.ai/api/v2/task/sync"
HIVE_TIMEOUT_SECONDS: int = 30

# ── ML Model ─────────────────────────────────────────────────────────────────
MODEL_PATH: str = os.path.join(os.path.dirname(__file__), "trained_model", "rf_model.joblib")
SCALER_PATH: str = os.path.join(os.path.dirname(__file__), "trained_model", "scaler.joblib")

# ── Decision Engine Thresholds (adaptive — data-driven) ──────────────────────
HIGH_RISK_THRESHOLD: float = 0.65   # ML risk score above this → HIGH_RISK
LOW_CONFIDENCE_UPPER: float = 0.60  # image confidence below this → SUSPICIOUS

# ── Server ────────────────────────────────────────────────────────────────────
HOST: str = "0.0.0.0"
PORT: int = 8000
DEBUG: bool = True

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = "INFO"
LOG_FILE: str = "app.log"
