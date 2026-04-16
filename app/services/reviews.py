from enum import Enum

from app.models.contracts import (
    AdminReviewRequest,
    AdminReviewResponse,
    ClassifyRoomResponse,
    ImageQualityResult,
    ModelUsage,
    PredictionListResponse,
    PredictionRecordResponse,
    PredictionSummaryResponse,
    RecommendedAction,
)
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

    def get_prediction(self, *, prediction_id: str) -> PredictionRecordResponse:
        record = self.repository.get_prediction(prediction_id)
        if record is None:
            raise KeyError(prediction_id)
        return _normalize_prediction_record(record)

    def list_predictions(
        self,
        *,
        limit: int = 20,
        pending_only: bool = False,
        reviewed_only: bool = False,
    ) -> PredictionListResponse:
        records = self.repository.list_predictions(
            limit=limit,
            pending_only=pending_only,
            reviewed_only=reviewed_only,
        )
        return PredictionListResponse(
            predictions=[_normalize_prediction_record(record) for record in records]
        )

    def get_summary(self) -> PredictionSummaryResponse:
        summary = self.repository.get_summary()
        return PredictionSummaryResponse(**summary)


def _normalize_prediction_record(record: dict[str, object]) -> PredictionRecordResponse:
    response = dict(record.get("response", {}))
    prediction_id = str(record.get("prediction_id", ""))
    normalized_response = ClassifyRoomResponse(
        prediction_id=str(response.get("prediction_id") or prediction_id),
        classification=_enum_or_value(response.get("classification", "borderline")),
        confidence=float(response.get("confidence", 0.5) or 0.5),
        needs_review=bool(response.get("needs_review", True)),
        recommended_action=_enum_or_value(
            response.get("recommended_action", RecommendedAction.ESCALATE.value)
        ),
        visible_reasons=[str(item) for item in response.get("visible_reasons", [])],
        image_quality=ImageQualityResult(
            **response.get(
                "image_quality",
                {
                    "is_acceptable": True,
                    "reason": "Legacy record; image quality details not captured.",
                    "retake_guidance": "None.",
                },
            )
        ),
        model_version=str(response.get("model_version", "legacy-unknown")),
        model_usage=ModelUsage(**response.get("model_usage", {})),
    )

    normalized_record = {
        "prediction_id": prediction_id,
        "image_reference": str(record.get("image_reference", "")),
        "source": record.get("source"),
        "room_type": record.get("room_type"),
        "response": normalized_response,
        "created_at": str(
            record.get("created_at")
            or record.get("updated_at")
            or "legacy-record"
        ),
        "updated_at": (
            str(record["updated_at"]) if record.get("updated_at") is not None else None
        ),
        "admin_review": record.get("admin_review"),
    }
    return PredictionRecordResponse(**normalized_record)


def _enum_or_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    return value
