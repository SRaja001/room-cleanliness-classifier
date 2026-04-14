from app.core.config import AppConfig
from app.models.contracts import (
    ModelUsage,
    ClassificationLabel,
    ClassifyRoomRequest,
    ImageQualityResult,
)
from app.services.bedrock import BedrockClassificationResult
from app.services.classifier import ClassifierService
from app.services.repository import InMemoryPredictionRepository
from app.services.storage import ImageStorageClient


class StubBedrockClient:
    def analyze_cleanliness(self, *, image_reference: str) -> BedrockClassificationResult:
        assert image_reference.startswith("s3://")
        return BedrockClassificationResult(
            classification=ClassificationLabel.CLEAN,
            confidence=0.72,
            visible_reasons=["Room appears mostly tidy."],
            usage=ModelUsage(
                input_tokens=1000,
                output_tokens=100,
                total_tokens=1100,
                estimated_cost_usd=0.00021,
            ),
            model_version="test-model",
        )


class StubRekognitionClient:
    def assess_image_quality(self, *, image_reference: str) -> ImageQualityResult:
        assert image_reference.startswith("s3://")
        return ImageQualityResult(
            is_acceptable=True,
            reason="Looks usable.",
            retake_guidance="None.",
        )


class StubStorageClient(ImageStorageClient):
    def __init__(self) -> None:
        super().__init__(config=AppConfig())

    def store_inline_image(self, *, image_base64: str) -> str:
        assert image_base64 == "cGxhY2Vob2xkZXI="
        return "s3://test-bucket/uploaded-image"


def test_classifier_saves_prediction_and_applies_review_policy() -> None:
    repository = InMemoryPredictionRepository()
    service = ClassifierService(
        rekognition_client=StubRekognitionClient(),
        bedrock_client=StubBedrockClient(),
        storage_client=StubStorageClient(),
        repository=repository,
    )

    result = service.classify(
        request=ClassifyRoomRequest(
            image_base64="cGxhY2Vob2xkZXI=",
            source="test-suite",
            room_type="bedroom",
        )
    )

    assert result.classification == ClassificationLabel.BORDERLINE
    assert result.needs_review is True
    assert result.prediction_id
    assert result.model_usage.input_tokens == 1000
    assert result.model_version == "test-model"
    assert len(repository.records) == 1
    saved_record = repository.get_prediction(result.prediction_id)
    assert saved_record is not None
    assert saved_record["image_reference"] == "s3://test-bucket/uploaded-image"
