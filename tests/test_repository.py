from app.models.contracts import AdminReviewRequest, ClassificationLabel
from app.services.repository import (
    DynamoDbPredictionRepository,
    InMemoryPredictionRepository,
)


class FakeDynamoTable:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, object]] = {}

    def put_item(self, *, Item: dict[str, object]) -> None:
        self.items[str(Item["prediction_id"])] = Item

    def get_item(self, *, Key: dict[str, object]) -> dict[str, object]:
        prediction_id = str(Key["prediction_id"])
        item = self.items.get(prediction_id)
        return {"Item": item} if item else {}

    def update_item(
        self,
        *,
        Key: dict[str, object],
        UpdateExpression: str,
        ExpressionAttributeValues: dict[str, object],
        ConditionExpression: str,
        ReturnValues: str,
    ) -> dict[str, object]:
        _ = UpdateExpression, ConditionExpression, ReturnValues
        prediction_id = str(Key["prediction_id"])
        item = self.items.get(prediction_id)
        if item is None:
            raise KeyError(prediction_id)
        item["admin_review"] = ExpressionAttributeValues[":review"]
        item["updated_at"] = ExpressionAttributeValues[":updated_at"]
        return {"Attributes": item}


def test_in_memory_repository_round_trip() -> None:
    repository = InMemoryPredictionRepository()
    saved = repository.save_prediction({"source": "test-suite"})

    loaded = repository.get_prediction(saved["prediction_id"])

    assert loaded is not None
    assert loaded["prediction_id"] == saved["prediction_id"]


def test_dynamodb_repository_round_trip_and_review() -> None:
    repository = DynamoDbPredictionRepository(table=FakeDynamoTable())
    saved = repository.save_prediction({"source": "test-suite"})

    loaded = repository.get_prediction(saved["prediction_id"])
    review = repository.save_admin_review(
        prediction_id=saved["prediction_id"],
        review=AdminReviewRequest(
            final_classification=ClassificationLabel.DIRTY,
            admin_comment="Visible trash remains.",
            reviewer="admin-user",
        ),
    )

    assert loaded is not None
    assert loaded["record_type"] == "prediction"
    assert review["prediction_id"] == saved["prediction_id"]
    assert review["final_classification"] == "dirty"
