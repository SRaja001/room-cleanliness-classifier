from app.core.config import AppConfig
from app.models.contracts import ImageQualityResult
from app.services.storage import parse_s3_uri


class RekognitionClient:
    """Image quality adapter that can use Rekognition when enabled."""

    def __init__(
        self,
        *,
        config: AppConfig,
        rekognition_client: object | None = None,
    ) -> None:
        self.config = config
        self.rekognition_client = rekognition_client

    def assess_image_quality(self, *, image_reference: str) -> ImageQualityResult:
        if not (self.config.aws_integration_enabled and self.config.rekognition_enabled):
            return ImageQualityResult(
                is_acceptable=True,
                reason="Image quality checks are not configured yet.",
                retake_guidance="None.",
            )

        if self.rekognition_client is None:
            raise RuntimeError(
                "Rekognition client is required when AWS integration is enabled."
            )

        bucket, key = parse_s3_uri(image_reference)
        response = self.rekognition_client.detect_labels(
            Image={"S3Object": {"Bucket": bucket, "Name": key}},
            Features=["IMAGE_PROPERTIES"],
        )
        image_properties = response.get("ImageProperties", {})
        quality = image_properties.get("Quality", {})
        brightness = float(quality.get("Brightness", 0.0))
        sharpness = float(quality.get("Sharpness", 0.0))
        is_acceptable = (
            brightness >= self.config.minimum_brightness
            and sharpness >= self.config.minimum_sharpness
        )
        if is_acceptable:
            return ImageQualityResult(
                is_acceptable=True,
                reason=(
                    f"Image quality passed with brightness {brightness:.1f} "
                    f"and sharpness {sharpness:.1f}."
                ),
                retake_guidance="None.",
            )

        return ImageQualityResult(
            is_acceptable=False,
            reason=(
                f"Image quality is too low with brightness {brightness:.1f} "
                f"and sharpness {sharpness:.1f}."
            ),
            retake_guidance=(
                "Retake the image in better lighting and keep the room in sharp focus."
            ),
        )
