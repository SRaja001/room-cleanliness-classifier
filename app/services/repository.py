import uuid
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


class InMemoryPredictionRepository:
    """Default repository for local development and tests."""

    def __init__(self) -> None:
        self.records: dict[str, dict[str, object]] = {}

    def save_prediction(self, payload: dict[str, object]) -> dict[str, object]:
        prediction_id = str(uuid.uuid4())
        record = {"prediction_id": prediction_id, **payload}
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
        return review_record


class DynamoDbPredictionRepository:
    """DynamoDB-backed repository for predictions and admin reviews."""

    def __init__(self, *, table: object) -> None:
        self.table = table

    def save_prediction(self, payload: dict[str, object]) -> dict[str, object]:
        prediction_id = str(uuid.uuid4())
        record = {
            "prediction_id": prediction_id,
            "record_type": "prediction",
            **payload,
        }
        self.table.put_item(Item=_to_dynamodb_compatible(record))
        return record

    def get_prediction(self, prediction_id: str) -> dict[str, object] | None:
        response = self.table.get_item(Key={"prediction_id": prediction_id})
        return response.get("Item")

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
                ":updated_at": "pending-timestamp",
            },
            ConditionExpression="attribute_exists(prediction_id)",
            ReturnValues="ALL_NEW",
        )
        attributes = response.get("Attributes")
        if not attributes or "admin_review" not in attributes:
            raise KeyError(prediction_id)
        return attributes["admin_review"]


def _to_dynamodb_compatible(value: object) -> object:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: _to_dynamodb_compatible(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_dynamodb_compatible(item) for item in value]
    return value
