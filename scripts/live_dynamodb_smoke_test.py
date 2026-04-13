import os
import sys

import boto3

from app.models.contracts import AdminReviewRequest, ClassificationLabel
from app.services.repository import DynamoDbPredictionRepository


def main() -> int:
    region = os.getenv("AWS_REGION", "us-east-1")
    table_name = os.getenv(
        "DYNAMODB_TABLE_NAME", "room-cleanliness-predictions-dev"
    )

    session = boto3.Session(region_name=region)
    table = session.resource("dynamodb").Table(table_name)
    repository = DynamoDbPredictionRepository(table=table)

    saved = repository.save_prediction(
        {
            "image_reference": "s3://manual-smoke-test/example.jpg",
            "response": {
                "classification": "borderline",
                "confidence": 0.5,
                "needs_review": True,
            },
            "source": "live-smoke-test",
            "room_type": "bedroom",
        }
    )
    prediction_id = str(saved["prediction_id"])
    loaded = repository.get_prediction(prediction_id)
    review = repository.save_admin_review(
        prediction_id=prediction_id,
        review=AdminReviewRequest(
            final_classification=ClassificationLabel.DIRTY,
            admin_comment="Smoke test review saved successfully.",
            reviewer="codex-live-test",
        ),
    )

    print(f"Saved prediction: {prediction_id}")
    print(f"Loaded item exists: {loaded is not None}")
    print(f"Review classification: {review['final_classification']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
