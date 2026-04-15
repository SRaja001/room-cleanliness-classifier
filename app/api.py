from fastapi import FastAPI, HTTPException

from app.core.config import AppConfig
from app.models.contracts import (
    AdminReviewRequest,
    AdminReviewResponse,
    ClassifyRoomRequest,
    ClassifyRoomResponse,
    HealthResponse,
    PredictionListResponse,
    PredictionRecordResponse,
    PredictionSummaryResponse,
)
from app.services.factory import create_application_services


def create_app(config: AppConfig | None = None) -> FastAPI:
    app_config = config or AppConfig.from_env()
    services = create_application_services(config=app_config)
    app = FastAPI(
        title="Room Cleanliness Classifier",
        version=app_config.app_version,
        description="Internal service for room cleanliness classification.",
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", app_name=app_config.app_name)

    @app.post("/classify", response_model=ClassifyRoomResponse)
    def classify_room_cleanliness(request: ClassifyRoomRequest) -> ClassifyRoomResponse:
        result = services.classifier_service.classify(request=request)
        return result

    @app.post("/predictions/{prediction_id}/review", response_model=AdminReviewResponse)
    def submit_admin_review(
        prediction_id: str, request: AdminReviewRequest
    ) -> AdminReviewResponse:
        try:
            return services.review_service.submit_review(
                prediction_id=prediction_id,
                review=request,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Prediction not found.") from exc

    @app.get("/predictions/{prediction_id}", response_model=PredictionRecordResponse)
    def get_prediction(prediction_id: str) -> PredictionRecordResponse:
        try:
            return services.review_service.get_prediction(prediction_id=prediction_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Prediction not found.") from exc

    @app.get("/predictions", response_model=PredictionListResponse)
    def list_predictions(
        limit: int = 20,
        pending_only: bool = False,
    ) -> PredictionListResponse:
        return services.review_service.list_predictions(
            limit=limit,
            pending_only=pending_only,
        )

    @app.get("/reports/summary", response_model=PredictionSummaryResponse)
    def get_prediction_summary() -> PredictionSummaryResponse:
        return services.review_service.get_summary()

    return app
