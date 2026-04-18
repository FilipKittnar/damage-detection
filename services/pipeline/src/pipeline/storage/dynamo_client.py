import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class DynamoClient:
    def __init__(self, table_name: str, region: str, endpoint_url: str | None):
        kwargs: dict = {"region_name": region}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        self._table = boto3.resource("dynamodb", **kwargs).Table(table_name)

    def create_job(self, job_id: str, input_path: str, output_path: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._table.put_item(Item={
            "job_id": job_id,
            "status": "pending",
            "input_path": input_path,
            "output_path": output_path,
            "created_at": now,
            "updated_at": now,
        })
        logger.info("created_job", extra={"job_id": job_id})

    def get_job(self, job_id: str) -> dict | None:
        resp = self._table.get_item(Key={"job_id": job_id})
        return resp.get("Item")

    def update_job_status(
        self,
        job_id: str,
        expected_current: str,
        new_status: str,
        error: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        expr = "SET #s = :new_status, updated_at = :now"
        values: dict = {":new_status": new_status, ":now": now, ":expected": expected_current}
        attr_names: dict = {"#s": "status"}
        if error is not None:
            expr += ", #e = :error"
            values[":error"] = error
            attr_names["#e"] = "error"
        self._table.update_item(
            Key={"job_id": job_id},
            UpdateExpression=expr,
            ConditionExpression="#s = :expected",
            ExpressionAttributeNames=attr_names,
            ExpressionAttributeValues=values,
        )
        logger.info("updated_job_status", extra={"job_id": job_id, "status": new_status})

    def update_job_counters(
        self,
        job_id: str,
        frame_count: int,
        damage_frame_count: int,
        blurred_frame_count: int,
    ) -> None:
        self._table.update_item(
            Key={"job_id": job_id},
            UpdateExpression=(
                "SET frame_count = :fc, damage_frame_count = :dfc, blurred_frame_count = :bfc"
            ),
            ExpressionAttributeValues={
                ":fc": frame_count,
                ":dfc": damage_frame_count,
                ":bfc": blurred_frame_count,
            },
        )

    def scan_jobs_by_status(self, status: str) -> list[dict]:
        resp = self._table.scan(
            FilterExpression="#s = :status",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":status": status},
        )
        return resp.get("Items", [])
