from app.core.config import AppConfig
from app.models.contracts import ImageQualityResult
from app.services.bedrock import BedrockVisionClient
from app.services.rekognition import RekognitionClient
from app.services.storage import (
    ImageStorageClient,
    decode_base64_image,
    infer_content_type,
    infer_image_extension,
    parse_s3_uri,
)


class FakeS3Client:
    def __init__(self) -> None:
        self.put_calls: list[dict[str, object]] = []
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, **kwargs) -> None:
        self.put_calls.append(kwargs)
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]

    def get_object(self, **kwargs) -> dict[str, object]:
        data = self.objects[(kwargs["Bucket"], kwargs["Key"])]
        return {"Body": FakeBody(data)}


class FakeBody:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return self.payload


class FakeRekognitionClient:
    def detect_labels(self, **kwargs) -> dict[str, object]:
        assert kwargs["Features"] == ["IMAGE_PROPERTIES"]
        return {
            "ImageProperties": {
                "Quality": {
                    "Brightness": 22.0,
                    "Sharpness": 18.0,
                }
            }
        }


class FakeBedrockClient:
    def converse(self, **kwargs) -> dict[str, object]:
        assert kwargs["modelId"] == "test-model"
        return {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": (
                                '{"classification":"dirty","confidence":0.97,'
                                '"visible_reasons":["Visible trash","Unmade bed"]}'
                            )
                        }
                    ]
                }
            }
        }


def test_storage_client_puts_images_in_s3_when_enabled() -> None:
    config = AppConfig(
        aws_integration_enabled=True,
        s3_enabled=True,
        s3_bucket_name="test-bucket",
        s3_key_prefix="incoming",
    )
    s3_client = FakeS3Client()
    storage = ImageStorageClient(config=config, s3_client=s3_client)

    s3_uri = storage.store_inline_image(image_base64="aGVsbG8=")

    assert s3_uri.startswith("s3://test-bucket/incoming/")
    assert len(s3_client.put_calls) == 1


def test_rekognition_client_returns_retake_guidance_for_low_quality() -> None:
    client = RekognitionClient(
        config=AppConfig(
            aws_integration_enabled=True,
            rekognition_enabled=True,
            minimum_brightness=35.0,
            minimum_sharpness=25.0,
        ),
        rekognition_client=FakeRekognitionClient(),
    )

    result = client.assess_image_quality(image_reference="s3://bucket/test.jpg")

    assert result == ImageQualityResult(
        is_acceptable=False,
        reason="Image quality is too low with brightness 22.0 and sharpness 18.0.",
        retake_guidance="Retake the image in better lighting and keep the room in sharp focus.",
    )


def test_bedrock_client_parses_structured_response() -> None:
    config = AppConfig(
        aws_integration_enabled=True,
        bedrock_enabled=True,
        bedrock_model_id="test-model",
        s3_bucket_name="test-bucket",
    )
    s3_client = FakeS3Client()
    storage = ImageStorageClient(config=config, s3_client=s3_client)
    bucket, key = "test-bucket", "uploads/image.jpg"
    s3_client.objects[(bucket, key)] = b"fake-image"
    client = BedrockVisionClient(
        config=config,
        bedrock_client=FakeBedrockClient(),
        storage_client=storage,
    )

    classification, confidence, reasons = client.analyze_cleanliness(
        image_reference="s3://test-bucket/uploads/image.jpg"
    )

    assert classification.value == "dirty"
    assert confidence == 0.97
    assert reasons == ["Visible trash", "Unmade bed"]


def test_parse_s3_uri_and_decode_base64_helpers() -> None:
    assert parse_s3_uri("s3://bucket/path/to/file.jpg") == ("bucket", "path/to/file.jpg")
    assert decode_base64_image("data:image/jpeg;base64,aGVsbG8=") == b"hello"
    assert infer_content_type("data:image/png;base64,aGVsbG8=") == "image/png"
    assert infer_image_extension("data:image/png;base64,aGVsbG8=") == "png"
