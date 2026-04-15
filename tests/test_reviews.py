from app.models.contracts import AdminReviewRequest, ClassificationLabel
from app.services.repository import InMemoryPredictionRepository
from app.services.reviews import ReviewService


def test_review_service_saves_admin_review() -> None:
    repository = InMemoryPredictionRepository()
    saved = repository.save_prediction(
        {
            "image_reference": "s3://bucket/image.jpg",
            "response": {"classification": "borderline"},
            "source": "test-suite",
            "room_type": "bedroom",
        }
    )
    review_service = ReviewService(repository=repository)

    response = review_service.submit_review(
        prediction_id=str(saved["prediction_id"]),
        review=AdminReviewRequest(
            final_classification=ClassificationLabel.DIRTY,
            admin_comment="Visible trash remains.",
            reviewer="admin-user",
        ),
    )

    assert response.prediction_id == saved["prediction_id"]
    assert response.final_classification == ClassificationLabel.DIRTY


def test_review_service_lists_predictions_and_summary() -> None:
    repository = InMemoryPredictionRepository()
    saved = repository.save_prediction(
        {
            "image_reference": "s3://bucket/image.jpg",
            "response": {
                "prediction_id": "placeholder",
                "classification": "borderline",
                "confidence": 0.7,
                "needs_review": True,
                "recommended_action": "escalate",
                "visible_reasons": ["Needs review."],
                "image_quality": {
                    "is_acceptable": True,
                    "reason": "Looks usable.",
                    "retake_guidance": "None.",
                },
                "model_version": "test-model",
                "model_usage": {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15,
                    "estimated_cost_usd": 0.00001,
                },
            },
            "source": "test-suite",
            "room_type": "bedroom",
        }
    )
    review_service = ReviewService(repository=repository)

    prediction = review_service.get_prediction(prediction_id=saved["prediction_id"])
    listed = review_service.list_predictions(limit=10)
    summary = review_service.get_summary()

    assert prediction.prediction_id == saved["prediction_id"]
    assert len(listed.predictions) == 1
    assert listed.predictions[0].prediction_id == saved["prediction_id"]
    assert summary.total_predictions == 1
    assert summary.pending_review == 1


def test_review_service_normalizes_legacy_prediction_records() -> None:
    repository = InMemoryPredictionRepository()
    saved = repository.save_prediction(
        {
            "image_reference": "s3://bucket/image.jpg",
            "response": {
                "classification": "borderline",
                "confidence": 0.5,
                "needs_review": True,
            },
            "source": "legacy-test",
            "room_type": "bedroom",
        }
    )
    repository.records[saved["prediction_id"]].pop("created_at", None)
    review_service = ReviewService(repository=repository)

    prediction = review_service.get_prediction(prediction_id=saved["prediction_id"])

    assert prediction.prediction_id == saved["prediction_id"]
    assert prediction.response.prediction_id == saved["prediction_id"]
    assert prediction.response.recommended_action == "escalate"
    assert prediction.response.model_version == "legacy-unknown"


def test_review_service_can_filter_pending_predictions() -> None:
    repository = InMemoryPredictionRepository()
    first = repository.save_prediction(
        {
            "image_reference": "s3://bucket/1.jpg",
            "response": {"classification": "dirty", "model_usage": {}},
            "source": "test-suite",
            "room_type": "bedroom",
        }
    )
    second = repository.save_prediction(
        {
            "image_reference": "s3://bucket/2.jpg",
            "response": {"classification": "clean", "model_usage": {}},
            "source": "test-suite",
            "room_type": "bedroom",
        }
    )
    repository.save_admin_review(
        prediction_id=first["prediction_id"],
        review=AdminReviewRequest(
            final_classification=ClassificationLabel.DIRTY,
            admin_comment="Reviewed.",
            reviewer="admin-user",
        ),
    )
    review_service = ReviewService(repository=repository)

    pending = review_service.list_predictions(limit=10, pending_only=True)

    assert len(pending.predictions) == 1
    assert pending.predictions[0].prediction_id == second["prediction_id"]
