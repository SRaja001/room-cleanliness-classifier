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
