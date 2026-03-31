# -*- coding: utf-8 -*-
"""
Entry Point — FastAPI HTTP server cho IoT Ingestion Module.

Endpoints:
  POST /predict   — Nhận dữ liệu đã feature-engineered, trả predicted_label + confidence
  GET  /health    — Health-check / readiness probe

Cách chạy:
  $ uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import db_connection, setup_indexes
from schemas import PredictRequest, PredictResponse
from service import get_model, predict_health_label

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("iot-ingestion.main")


# ── Lifespan (startup / shutdown) ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler — chạy khi khởi động và tắt server."""
    logger.info("=" * 60)
    logger.info("  IoMT — IoT INGESTION MODULE (FastAPI)")
    logger.info("  HTTP Predict API for Node-RED ETL pipeline")
    logger.info("=" * 60)

    # Setup MongoDB indexes
    try:
        db = db_connection.database
        await setup_indexes(db)
        logger.info("MongoDB indexes created/verified successfully")
    except Exception as e:
        logger.warning("Failed to setup MongoDB indexes: %s", e)

    # Pre-load ML model into cache
    try:
        get_model()
        logger.info("ML model pre-loaded successfully")
    except FileNotFoundError as e:
        logger.warning("ML model not available at startup: %s", e)
    except RuntimeError as e:
        logger.error("ML model load error: %s", e)

    yield  # ── Server chạy ──

    # Shutdown
    logger.info("Shutting down IoT Ingestion Module...")
    db_connection.close()
    logger.info("MongoDB connection closed. Goodbye.")


# ── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="IoMT Ingestion — Health Predict API",
    description="ML prediction endpoint for the IoT health monitoring streaming ETL pipeline.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — cho phép Node-RED và dashboard truy cập
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ───────────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    """Readiness probe — kiểm tra server + model sẵn sàng."""
    try:
        get_model()
        model_status = "loaded"
    except (FileNotFoundError, RuntimeError):
        model_status = "unavailable"

    return {
        "status": "ok",
        "model_status": model_status,
        "mongo_db": settings.MONGO_DB_NAME,
    }


@app.post("/predict", response_model=PredictResponse, tags=["prediction"])
async def predict(request: PredictRequest) -> PredictResponse:
    """
    Predict health label from feature-engineered sensor data.

    Called by Node-RED after it performs cleansing + feature engineering.
    Returns predicted_label and confidence score.
    """
    try:
        result = await predict_health_label(request.model_dump())
    except FileNotFoundError as e:
        logger.error("Model file not found: %s", e)
        raise HTTPException(
            status_code=503,
            detail="ML model is not available. Please train the model first.",
        ) from e
    except RuntimeError as e:
        logger.error("Model runtime error: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"ML model error: {e}",
        ) from e
    except KeyError as e:
        logger.error("Missing feature in payload: %s", e)
        raise HTTPException(
            status_code=422,
            detail=f"Missing required feature: {e}",
        ) from e

    return PredictResponse(**result)


# ── Run directly ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HTTP_HOST,
        port=settings.HTTP_PORT,
        reload=True,
    )
