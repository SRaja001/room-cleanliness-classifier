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

    def scan(self, *, Limit: int | None = None) -> dict[str, object]:
        items = list(self.items.values())
        if Limit is not None:
            items = items[:Limit]
        return {"Items": items}


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


def test_in_memory_repository_lists_predictions_and_builds_summary() -> None:
    repository = InMemoryPredictionRepository()
    first = repository.save_prediction(
        {
            "image_reference": "s3://bucket/1.jpg",
            "response": {
                "classification": "clean",
                "model_usage": {"estimated_cost_usd": 0.00011},
            },
            "source": "test-suite",
            "room_type": "bedroom",
        }
    )
    second = repository.save_prediction(
        {
            "image_reference": "s3://bucket/2.jpg",
            "response": {
                "classification": "dirty",
                "model_usage": {"estimated_cost_usd": 0.00022},
            },
            "source": "test-suite",
            "room_type": "bedroom",
        }
    )
    repository.save_admin_review(
        prediction_id=first["prediction_id"],
        review=AdminReviewRequest(
            final_classification=ClassificationLabel.CLEAN,
            admin_comment="Looks good.",
            reviewer="admin-user",
        ),
    )

    records = repository.list_predictions(limit=10)
    summary = repository.get_summary()

    assert len(records) == 2
    assert records[0]["prediction_id"] == second["prediction_id"]
    assert summary["total_predictions"] == 2
    assert summary["reviewed_predictions"] == 1
    assert summary["pending_review"] == 1
    assert summary["classification_breakdown"]["clean"] == 1
    assert summary["classification_breakdown"]["dirty"] == 1
    assert summary["review_breakdown"]["clean"] == 1
    assert summary["total_estimated_cost_usd"] == 0.00033


def test_in_memory_repository_filters_pending_and_sorts_legacy_last() -> None:
    repository = InMemoryPredictionRepository()
    legacy = repository.save_prediction(
        {
            "image_reference": "s3://bucket/legacy.jpg",
            "response": {"classification": "borderline", "model_usage": {}},
            "source": "test-suite",
            "room_type": "bedroom",
        }
    )
    current = repository.save_prediction(
        {
            "image_reference": "s3://bucket/current.jpg",
            "response": {"classification": "clean", "model_usage": {}},
            "source": "test-suite",
            "room_type": "bedroom",
        }
    )
    repository.records[legacy["prediction_id"]]["created_at"] = "legacy-record"
    repository.records[legacy["prediction_id"]]["updated_at"] = "legacy-record"
    repository.save_admin_review(
        prediction_id=current["prediction_id"],
        review=AdminReviewRequest(
            final_classification=ClassificationLabel.CLEAN,
            admin_comment="Reviewed.",
            reviewer="admin-user",
        ),
    )

    records = repository.list_predictions(limit=10)
    pending_records = repository.list_predictions(limit=10, pending_only=True)

    assert records[0]["prediction_id"] == current["prediction_id"]
    assert records[-1]["prediction_id"] == legacy["prediction_id"]
    assert len(pending_records) == 1
    assert pending_records[0]["prediction_id"] == legacy["prediction_id"]
