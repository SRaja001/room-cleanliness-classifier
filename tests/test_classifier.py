from app.core.config import AppConfig
from app.models.contracts import (
    ClassificationLabel,
    ClassifyRoomRequest,
    ImageQualityResult,
)
from app.services.classifier import ClassifierService
from app.services.repository import InMemoryPredictionRepository
from app.services.storage import ImageStorageClient


class StubBedrockClient:
    def analyze_cleanliness(self, *, image_reference: str) -> tuple[ClassificationLabel, float, list[str]]:
        assert image_reference.startswith("s3://")
        return (ClassificationLabel.CLEAN, 0.72, ["Room appears mostly tidy."])


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
    assert len(repository.records) == 1
    saved_record = repository.get_prediction(result.prediction_id)
    assert saved_record is not None
    assert saved_record["image_reference"] == "s3://test-bucket/uploaded-image"
