from app.core.config import AppConfig
from app.models.contracts import (
    ClassifyRoomRequest,
    ClassifyRoomResponse,
)
from app.services.bedrock import BedrockVisionClient
from app.services.policy import ReviewPolicy
from app.services.rekognition import RekognitionClient
from app.services.repository import PredictionRepositoryProtocol
from app.services.storage import ImageStorageClient


class ClassifierService:
    def __init__(
        self,
        rekognition_client: RekognitionClient | None = None,
        bedrock_client: BedrockVisionClient | None = None,
        review_policy: ReviewPolicy | None = None,
        storage_client: ImageStorageClient | None = None,
        repository: PredictionRepositoryProtocol | None = None,
        config: AppConfig | None = None,
    ) -> None:
        self.config = config or AppConfig.from_env()
        self.storage_client = storage_client or ImageStorageClient(config=self.config)
        self.rekognition_client = rekognition_client or RekognitionClient(
            config=self.config
        )
        self.bedrock_client = bedrock_client or BedrockVisionClient(
            config=self.config,
            storage_client=self.storage_client,
        )
        self.review_policy = review_policy or ReviewPolicy(config=self.config)
        if repository is None:
            raise ValueError("ClassifierService requires a repository instance.")
        self.repository = repository

    def classify(self, *, request: ClassifyRoomRequest) -> ClassifyRoomResponse:
        image_reference = request.image_s3_uri or self.storage_client.store_inline_image(
            image_base64=request.image_base64 or ""
        )
        quality = self.rekognition_client.assess_image_quality(image_reference=image_reference)
        model_result = self.bedrock_client.analyze_cleanliness(
            image_reference=image_reference
        )
        decision = self.review_policy.apply(
            initial_label=model_result.classification,
            confidence=model_result.confidence,
            quality=quality,
        )
        response = ClassifyRoomResponse(
            prediction_id="",
            classification=decision["classification"],
            confidence=decision["confidence"],
            needs_review=decision["needs_review"],
            recommended_action=decision["recommended_action"],
            visible_reasons=model_result.visible_reasons,
            image_quality=quality,
            model_version=model_result.model_version,
            model_usage=model_result.usage,
        )
        saved_record = self.repository.save_prediction(
            {
                "image_reference": image_reference,
                "response": response.model_dump(),
                "source": request.source,
                "room_type": request.room_type,
            }
        )
        response.prediction_id = str(saved_record["prediction_id"])
        saved_record["response"] = response.model_dump()
        return response
