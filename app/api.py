from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response

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
from app.services.storage import infer_content_type_from_s3_uri
from app.ui import (
    render_prediction_page,
    render_review_queue_page,
    render_saved_reviews_page,
    render_staging_home,
    render_upload_page,
)


def create_app(config: AppConfig | None = None) -> FastAPI:
    app_config = config or AppConfig.from_env()
    services = create_application_services(config=app_config)
    app = FastAPI(
        title="Room Cleanliness Classifier",
        version=app_config.app_version,
        description="Internal service for room cleanliness classification.",
    )

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/staging", status_code=302)

    @app.get("/staging", response_class=HTMLResponse, include_in_schema=False)
    def staging_home() -> HTMLResponse:
        return HTMLResponse(render_staging_home())

    @app.get("/staging/upload", response_class=HTMLResponse, include_in_schema=False)
    def staging_upload_page() -> HTMLResponse:
        return HTMLResponse(render_upload_page())

    @app.get(
        "/staging/predictions/{prediction_id}",
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    def staging_prediction_page(prediction_id: str) -> HTMLResponse:
        return HTMLResponse(render_prediction_page(prediction_id))

    @app.get(
        "/staging/review-queue",
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    def staging_review_queue_page() -> HTMLResponse:
        return HTMLResponse(render_review_queue_page())

    @app.get(
        "/staging/saved-reviews",
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    def staging_saved_reviews_page() -> HTMLResponse:
        return HTMLResponse(render_saved_reviews_page())

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

    @app.get("/predictions/{prediction_id}/image", include_in_schema=False)
    def get_prediction_image(prediction_id: str) -> Response:
        try:
            prediction = services.review_service.get_prediction(prediction_id=prediction_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Prediction not found.") from exc

        try:
            image_bytes = services.classifier_service.storage_client.load_image_bytes(
                image_s3_uri=prediction.image_reference
            )
        except Exception as exc:
            raise HTTPException(
                status_code=404,
                detail="Prediction image is not available for preview.",
            ) from exc

        return Response(
            content=image_bytes,
            media_type=infer_content_type_from_s3_uri(prediction.image_reference),
        )

    @app.get("/predictions", response_model=PredictionListResponse)
    def list_predictions(
        limit: int = 20,
        pending_only: bool = False,
        reviewed_only: bool = False,
    ) -> PredictionListResponse:
        return services.review_service.list_predictions(
            limit=limit,
            pending_only=pending_only,
            reviewed_only=reviewed_only,
        )

    @app.get("/reports/summary", response_model=PredictionSummaryResponse)
    def get_prediction_summary() -> PredictionSummaryResponse:
        return services.review_service.get_summary()

    return app
