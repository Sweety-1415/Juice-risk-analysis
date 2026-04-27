from __future__ import annotations

import base64
import csv
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import cv2
import numpy as np
from ultralytics import YOLO

from app.data import BEVERAGE_LIBRARY

import os

BASE_DIR = Path(__file__).resolve().parents[2]
# Allow MODEL_PATH to be overridden via environment variable for cloud deployment
_env_model = os.environ.get("MODEL_PATH")
if _env_model:
    MODEL_PATH = Path(_env_model)
else:
    MODEL_PATH = BASE_DIR / "runs" / "detect" / "train" / "weights" / "best.pt"
    # Fallback: check root directory for .pt files
    if not MODEL_PATH.exists():
        for pt in BASE_DIR.glob("*.pt"):
            MODEL_PATH = pt
            break

RESULTS_CSV = BASE_DIR / "runs" / "detect" / "train" / "results.csv"
STATIC_DIR = BASE_DIR / "app" / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
CAPTURE_DIR = STATIC_DIR / "captures"

_model: YOLO | None = None
_model_load_error: str | None = None


def get_model() -> YOLO:
    global _model, _model_load_error
    if _model_load_error:
        raise RuntimeError(_model_load_error)
    if _model is None:
        if not MODEL_PATH.exists():
            _model_load_error = (
                f"YOLO model not found at {MODEL_PATH}. "
                "Please set the MODEL_PATH environment variable on the server."
            )
            raise RuntimeError(_model_load_error)
        try:
            _model = YOLO(str(MODEL_PATH))
        except Exception as exc:
            _model_load_error = f"Failed to load YOLO model: {exc}"
            raise RuntimeError(_model_load_error) from exc
    return _model


def _filename(prefix: str) -> str:
    return f"{prefix}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}.jpg"


def _save_image(image: np.ndarray, folder: Path, prefix: str) -> str:
    folder.mkdir(parents=True, exist_ok=True)
    filename = _filename(prefix)
    target = folder / filename
    cv2.imwrite(str(target), image)
    return f"{folder.name}/{filename}"


def _decode_base64_image(payload: str) -> np.ndarray:
    encoded = payload.split(",", 1)[1] if "," in payload else payload
    image_bytes = base64.b64decode(encoded)
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unable to decode webcam image.")
    return image


def _detect_from_image(image: np.ndarray) -> dict[str, Any]:
    result = get_model().predict(source=image, conf=0.35, verbose=False)[0]
    if result.boxes is None or len(result.boxes) == 0:
        return {
            "status": "not_detected",
            "confidence": None,
            "label": None,
            "display_name": None,
            "annotated_image": image,
        }

    confidences = result.boxes.conf.cpu().tolist()
    classes = result.boxes.cls.cpu().tolist()
    best_index = max(range(len(confidences)), key=lambda idx: confidences[idx])
    confidence = round(float(confidences[best_index]) * 100, 2)
    class_id = int(classes[best_index])
    raw_label = result.names[class_id]
    display_name = BEVERAGE_LIBRARY.get(raw_label, {}).get("display_name", raw_label.replace("_", " "))
    annotated = result.plot()

    return {
        "status": "detected",
        "confidence": confidence,
        "label": raw_label,
        "display_name": display_name,
        "annotated_image": annotated,
    }


def detect_upload(file_storage: Any) -> dict[str, Any]:
    image_bytes = file_storage.read()
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Uploaded file is not a valid image.")

    original_path = _save_image(image, UPLOAD_DIR, "upload")
    detection = _detect_from_image(image)
    annotated_path = _save_image(detection["annotated_image"], CAPTURE_DIR, "annotated")

    detection["image_path"] = original_path
    detection["annotated_path"] = annotated_path
    return detection


def detect_webcam(base64_payload: str) -> dict[str, Any]:
    image = _decode_base64_image(base64_payload)
    original_path = _save_image(image, CAPTURE_DIR, "capture")
    detection = _detect_from_image(image)
    annotated_path = _save_image(detection["annotated_image"], CAPTURE_DIR, "annotated")

    detection["image_path"] = original_path
    detection["annotated_path"] = annotated_path
    return detection


def training_metrics() -> dict[str, Any]:
    metrics = {
        "epochs": 0,
        "precision": 0.0,
        "recall": 0.0,
        "map50": 0.0,
        "map50_95": 0.0,
    }
    if not RESULTS_CSV.exists():
        return metrics

    with RESULTS_CSV.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return metrics

    last_row = rows[-1]
    metrics["epochs"] = int(float(last_row["epoch"]))
    metrics["precision"] = round(float(last_row["metrics/precision(B)"]) * 100, 2)
    metrics["recall"] = round(float(last_row["metrics/recall(B)"]) * 100, 2)
    metrics["map50"] = round(float(last_row["metrics/mAP50(B)"]) * 100, 2)
    metrics["map50_95"] = round(float(last_row["metrics/mAP50-95(B)"]) * 100, 2)
    return metrics
