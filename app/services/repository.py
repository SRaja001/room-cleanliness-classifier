import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol

from app.models.contracts import AdminReviewRequest


class PredictionRepositoryProtocol(Protocol):
    def save_prediction(self, payload: dict[str, object]) -> dict[str, object]:
        ...

    def get_prediction(self, prediction_id: str) -> dict[str, object] | None:
        ...

    def save_admin_review(
        self, *, prediction_id: str, review: AdminReviewRequest
    ) -> dict[str, object]:
        ...

    def list_predictions(
        self, *, limit: int, pending_only: bool = False
    ) -> list[dict[str, object]]:
        ...

    def get_summary(self) -> dict[str, object]:
        ...


class InMemoryPredictionRepository:
    """Default repository for local development and tests."""

    def __init__(self) -> None:
        self.records: dict[str, dict[str, object]] = {}

    def save_prediction(self, payload: dict[str, object]) -> dict[str, object]:
        prediction_id = str(uuid.uuid4())
        timestamp = _utc_timestamp()
        record = {
            "prediction_id": prediction_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            **payload,
        }
        self.records[prediction_id] = record
        return record

    def get_prediction(self, prediction_id: str) -> dict[str, object] | None:
        return self.records.get(prediction_id)

    def save_admin_review(
        self, *, prediction_id: str, review: AdminReviewRequest
    ) -> dict[str, object]:
        record = self.records.get(prediction_id)
        if record is None:
            raise KeyError(prediction_id)

        review_record = {
            "prediction_id": prediction_id,
            "final_classification": review.final_classification.value,
            "admin_comment": review.admin_comment,
            "reviewer": review.reviewer,
        }
        record["admin_review"] = review_record
        record["updated_at"] = _utc_timestamp()
        return review_record

    def list_predictions(
        self, *, limit: int, pending_only: bool = False
    ) -> list[dict[str, object]]:
        records = list(self.records.values())
        if pending_only:
            records = [record for record in records if "admin_review" not in record]
        records.sort(key=_record_sort_key, reverse=True)
        return records[:limit]

    def get_summary(self) -> dict[str, object]:
        return _build_summary(self.records.values())


class DynamoDbPredictionRepository:
    """DynamoDB-backed repository for predictions and admin reviews."""

    def __init__(self, *, table: object) -> None:
        self.table = table

    def save_prediction(self, payload: dict[str, object]) -> dict[str, object]:
        prediction_id = str(uuid.uuid4())
        timestamp = _utc_timestamp()
        record = {
            "prediction_id": prediction_id,
            "record_type": "prediction",
            "created_at": timestamp,
            "updated_at": timestamp,
            **payload,
        }
        self.table.put_item(Item=_to_dynamodb_compatible(record))
        return record

    def get_prediction(self, prediction_id: str) -> dict[str, object] | None:
        response = self.table.get_item(Key={"prediction_id": prediction_id})
        item = response.get("Item")
        if item is None:
            return None
        return _from_dynamodb_compatible(item)

    def save_admin_review(
        self, *, prediction_id: str, review: AdminReviewRequest
    ) -> dict[str, object]:
        response = self.table.update_item(
            Key={"prediction_id": prediction_id},
            UpdateExpression=(
                "SET admin_review = :review, "
                "updated_at = :updated_at"
            ),
            ExpressionAttributeValues={
                ":review": _to_dynamodb_compatible(
                    {
                        "prediction_id": prediction_id,
                        "final_classification": review.final_classification.value,
                        "admin_comment": review.admin_comment,
                        "reviewer": review.reviewer,
                    }
                ),
                ":updated_at": _utc_timestamp(),
            },
            ConditionExpression="attribute_exists(prediction_id)",
            ReturnValues="ALL_NEW",
        )
        attributes = response.get("Attributes")
        if not attributes or "admin_review" not in attributes:
            raise KeyError(prediction_id)
        return _from_dynamodb_compatible(attributes["admin_review"])

    def list_predictions(
        self, *, limit: int, pending_only: bool = False
    ) -> list[dict[str, object]]:
        response = self.table.scan()
        items = [_from_dynamodb_compatible(item) for item in response.get("Items", [])]
        records = [item for item in items if item.get("record_type") == "prediction"]
        if pending_only:
            records = [record for record in records if "admin_review" not in record]
        records.sort(key=_record_sort_key, reverse=True)
        return records[:limit]

    def get_summary(self) -> dict[str, object]:
        response = self.table.scan()
        items = [_from_dynamodb_compatible(item) for item in response.get("Items", [])]
        records = [item for item in items if item.get("record_type") == "prediction"]
        return _build_summary(records)


def _to_dynamodb_compatible(value: object) -> object:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: _to_dynamodb_compatible(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_dynamodb_compatible(item) for item in value]
    return value


def _from_dynamodb_compatible(value: object) -> object:
    if isinstance(value, Decimal):
        if value == value.to_integral():
            return int(value)
        return float(value)
    if isinstance(value, dict):
        return {key: _from_dynamodb_compatible(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_from_dynamodb_compatible(item) for item in value]
    return value


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_sort_key(record: dict[str, object]) -> tuple[int, datetime]:
    created_at = _parse_timestamp(record.get("created_at"))
    updated_at = _parse_timestamp(record.get("updated_at"))
    best_timestamp = created_at or updated_at
    if best_timestamp is None:
        return (0, datetime.min.replace(tzinfo=timezone.utc))
    return (1, best_timestamp)


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _build_summary(records: object) -> dict[str, object]:
    record_list = list(records)
    classification_breakdown = {"clean": 0, "borderline": 0, "dirty": 0}
    review_breakdown = {"clean": 0, "borderline": 0, "dirty": 0}
    total_estimated_cost_usd = 0.0
    reviewed_predictions = 0

    for record in record_list:
        response = record.get("response", {})
        classification = str(response.get("classification", ""))
        if classification in classification_breakdown:
            classification_breakdown[classification] += 1

        model_usage = response.get("model_usage", {})
        total_estimated_cost_usd += float(model_usage.get("estimated_cost_usd", 0.0) or 0.0)

        admin_review = record.get("admin_review")
        if isinstance(admin_review, dict):
            reviewed_predictions += 1
            final_classification = str(admin_review.get("final_classification", ""))
            if final_classification in review_breakdown:
                review_breakdown[final_classification] += 1

    total_predictions = len(record_list)
    return {
        "total_predictions": total_predictions,
        "reviewed_predictions": reviewed_predictions,
        "pending_review": total_predictions - reviewed_predictions,
        "total_estimated_cost_usd": round(total_estimated_cost_usd, 8),
        "classification_breakdown": classification_breakdown,
        "review_breakdown": review_breakdown,
    }
