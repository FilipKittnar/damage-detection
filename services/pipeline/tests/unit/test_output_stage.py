import numpy as np
import cv2
import pytest
from unittest.mock import MagicMock, patch

from pipeline.stages.output_stage import OutputStage


def _make_jpeg() -> bytes:
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


def test_output_stage_calls_upload_with_correct_args():
    mock_s3 = MagicMock()
    stage = OutputStage(s3_client=mock_s3, bucket="test-bucket")
    jpeg = _make_jpeg()
    stage.process(jpeg, job_id="fleet/job1/clip.mp4", frame_index=5)
    mock_s3.upload_frame.assert_called_once_with(
        "test-bucket", "fleet/job1/clip.mp4", 5, jpeg
    )


def test_output_stage_uploads_each_frame():
    mock_s3 = MagicMock()
    stage = OutputStage(s3_client=mock_s3, bucket="test-bucket")
    for i in range(3):
        stage.process(_make_jpeg(), job_id="job1/v.mp4", frame_index=i)
    assert mock_s3.upload_frame.call_count == 3
