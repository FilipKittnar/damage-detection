# Contract: Licence Plate Blurring Service

**Service**: `plate-blurring`
**Base URL (local)**: `http://plate-blurring:8001`
**Protocol**: HTTP/1.1, JSON responses

---

## POST /v1/blur

Accepts an image file, detects all vehicle licence plates, blurs them, and returns the processed image along with detection metadata.

This endpoint is called by the Pipeline Service for every frame before it is written to S3. If this endpoint is unavailable or returns an error, the Pipeline Service MUST fail the job (FR-010).

### Request

**Content-Type**: `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | Binary (JPEG/PNG) | Yes | Raw image bytes of the frame to process. |
| `job_id` | String | Yes | Job ID for logging and traceability. |
| `frame_index` | Integer | Yes | Zero-based frame index for logging. |

### Response — 200 OK

**Content-Type**: `application/json`

```json
{
  "image_b64": "<base64-encoded JPEG bytes of the blurred image>",
  "plates_detected": 2,
  "bounding_boxes": [
    { "x1": 120, "y1": 540, "x2": 280, "y2": 580, "confidence": 0.94, "label": "licence_plate" },
    { "x1": 900, "y1": 430, "x2": 1060, "y2": 470, "confidence": 0.88, "label": "licence_plate" }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `image_b64` | String | Base64-encoded JPEG of the processed frame with all licence plates blurred. |
| `plates_detected` | Integer | Number of plates found and blurred. 0 if none detected. |
| `bounding_boxes` | Array[BoundingBox] | Coordinates of each detected plate (pixel, absolute). |

### Response — 422 Unprocessable Entity

Returned when the uploaded file cannot be decoded as an image.

```json
{
  "error": "invalid_image",
  "detail": "Could not decode image from uploaded bytes."
}
```

### Response — 503 Service Unavailable

Returned when the licence plate detection model is not loaded or has failed to initialise.

```json
{
  "error": "model_unavailable",
  "detail": "Licence plate detection model is not ready."
}
```

---

## GET /health

Liveness and readiness check. Returns 200 when the model is loaded and the service is ready to process requests.

### Response — 200 OK

```json
{
  "status": "ok",
  "model_loaded": true
}
```

### Response — 503 Service Unavailable

```json
{
  "status": "unavailable",
  "model_loaded": false
}
```

---

## BoundingBox Schema

Used in `POST /v1/blur` response.

| Field | Type | Description |
|-------|------|-------------|
| `x1` | Integer | Left pixel x-coordinate (absolute). |
| `y1` | Integer | Top pixel y-coordinate (absolute). |
| `x2` | Integer | Right pixel x-coordinate (absolute). |
| `y2` | Integer | Bottom pixel y-coordinate (absolute). |
| `confidence` | Float | Detection confidence, 0.0–1.0. |
| `label` | String | Always `"licence_plate"` for this service. |

---

## Pipeline Service Integration Notes

- The Pipeline Service calls `POST /v1/blur` for **every extracted frame**, regardless of whether damage was detected.
- If `plates_detected == 0`, the returned `image_b64` is the original frame re-encoded as JPEG (no visual change, but the pipeline still goes through the blurring service for auditability).
- The Pipeline Service decodes `image_b64` and uploads the resulting bytes to S3 as the output frame.
- If `POST /v1/blur` returns any non-200 response, or the request times out, the Pipeline Service transitions the job to `failed` and publishes a `JobFailed` event.
- The Pipeline Service MUST call `GET /health` during its own startup and refuse to process jobs if the blurring service is unreachable.

---

## Local Development

Service runs at `http://plate-blurring:8001` inside Docker Compose.
Health check: `curl http://localhost:8001/health`
