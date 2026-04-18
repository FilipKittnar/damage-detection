import base64
import logging

import httpx

logger = logging.getLogger(__name__)


class BlurServiceUnavailableError(Exception):
    pass


class BlurStage:
    def __init__(self, blurring_url: str, timeout: float = 30.0):
        self._url = blurring_url.rstrip("/")
        self._timeout = timeout

    def process(self, jpeg_bytes: bytes, job_id: str, frame_index: int) -> bytes:
        try:
            response = httpx.post(
                f"{self._url}/v1/blur",
                files={"file": ("frame.jpg", jpeg_bytes, "image/jpeg")},
                data={"job_id": job_id, "frame_index": str(frame_index)},
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise BlurServiceUnavailableError(f"Blurring service request failed: {exc}") from exc

        if response.status_code != 200:
            raise BlurServiceUnavailableError(
                f"Blurring service returned {response.status_code}"
            )

        image_b64 = response.json()["image_b64"]
        decoded = base64.b64decode(image_b64)
        logger.debug("blur_stage_done", extra={"job_id": job_id, "frame_index": frame_index})
        return decoded
