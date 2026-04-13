from app.models.contracts import AdminReviewRequest, AdminReviewResponse
from app.services.repository import PredictionRepositoryProtocol


class ReviewService:
    def __init__(self, *, repository: PredictionRepositoryProtocol) -> None:
        self.repository = repository

    def submit_review(
        self, *, prediction_id: str, review: AdminReviewRequest
    ) -> AdminReviewResponse:
        review_record = self.repository.save_admin_review(
            prediction_id=prediction_id,
            review=review,
        )
        return AdminReviewResponse(**review_record)
