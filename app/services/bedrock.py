import json

from app.core.config import AppConfig
from app.models.contracts import ClassificationLabel
from app.services.storage import ImageStorageClient


class BedrockVisionClient:
    """Vision classification adapter for placeholder and Bedrock-backed inference."""

    def __init__(
        self,
        *,
        config: AppConfig,
        storage_client: ImageStorageClient,
        bedrock_client: object | None = None,
    ) -> None:
        self.config = config
        self.storage_client = storage_client
        self.bedrock_client = bedrock_client

    def analyze_cleanliness(self, *, image_reference: str) -> tuple[ClassificationLabel, float, list[str]]:
        if not (self.config.aws_integration_enabled and self.config.bedrock_enabled):
            return (
                ClassificationLabel.BORDERLINE,
                0.5,
                ["Bedrock integration not configured yet; returning placeholder result."],
            )

        if self.bedrock_client is None:
            raise RuntimeError("Bedrock client is required when AWS integration is enabled.")

        response = self.bedrock_client.converse(
            modelId=self.config.bedrock_model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"text": _classification_prompt()},
                        {
                            "image": {
                                "format": self.storage_client.infer_image_format(
                                    image_s3_uri=image_reference
                                ),
                                "source": {
                                    "bytes": self.storage_client.load_image_bytes(
                                        image_s3_uri=image_reference
                                    )
                                },
                            }
                        },
                    ],
                }
            ],
        )
        content = response.get("output", {}).get("message", {}).get("content", [])
        raw_text = "".join(block.get("text", "") for block in content if "text" in block)
        parsed = _parse_bedrock_payload(raw_text)
        return (
            parsed["classification"],
            parsed["confidence"],
            parsed["visible_reasons"],
        )


def _classification_prompt() -> str:
    return (
        "You are classifying a room image for cleanliness. "
        "Return only JSON with keys classification, confidence, and visible_reasons. "
        "classification must be one of clean, borderline, dirty. "
        "Use a conservative standard: if uncertain, choose borderline."
    )


def _parse_bedrock_payload(payload: str) -> dict[str, object]:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("Bedrock response did not contain valid JSON.") from exc

    classification = ClassificationLabel(parsed["classification"])
    confidence = float(parsed["confidence"])
    visible_reasons = [str(item) for item in parsed.get("visible_reasons", [])]
    return {
        "classification": classification,
        "confidence": confidence,
        "visible_reasons": visible_reasons,
    }
