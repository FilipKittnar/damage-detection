import base64
import logging

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/v1/blur")
async def blur(
    request: Request,
    file: UploadFile = File(...),
    job_id: str = Form(...),
    frame_index: int = Form(...),
):
    detector = request.app.state.detector
    if detector is None:
        return JSONResponse(
            status_code=503,
            content={"error": "model_unavailable", "detail": "Licence plate detection model is not ready."},
        )

    raw = await file.read()
    arr = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        return JSONResponse(
            status_code=422,
            content={"error": "invalid_image", "detail": "Could not decode image from uploaded bytes."},
        )

    blurred_image, boxes = detector.detect_and_blur(image)
    _, buf = cv2.imencode(".jpg", blurred_image)
    image_b64 = base64.b64encode(buf.tobytes()).decode()

    box_list = [
        {
            "x1": b.x1, "y1": b.y1, "x2": b.x2, "y2": b.y2,
            "confidence": b.confidence, "label": b.label,
        }
        for b in boxes
    ]

    logger.info(
        "blur_request_processed",
        extra={"job_id": job_id, "frame_index": frame_index, "plates_detected": len(boxes)},
    )

    return {
        "image_b64": image_b64,
        "plates_detected": len(boxes),
        "bounding_boxes": box_list,
    }


@router.get("/health")
async def health(request: Request):
    detector = request.app.state.detector
    if detector is None:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "model_loaded": False},
        )
    return {"status": "ok", "model_loaded": True}
