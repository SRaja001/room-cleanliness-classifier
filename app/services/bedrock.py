import json
from dataclasses import dataclass

from app.core.config import AppConfig
from app.models.contracts import ClassificationLabel, ModelUsage
from app.services.storage import ImageStorageClient


@dataclass(frozen=True)
class BedrockClassificationResult:
    classification: ClassificationLabel
    confidence: float
    visible_reasons: list[str]
    usage: ModelUsage
    model_version: str


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

    def analyze_cleanliness(self, *, image_reference: str) -> BedrockClassificationResult:
        if not (self.config.aws_integration_enabled and self.config.bedrock_enabled):
            return BedrockClassificationResult(
                classification=ClassificationLabel.BORDERLINE,
                confidence=0.5,
                visible_reasons=[
                    "Bedrock integration not configured yet; returning placeholder result."
                ],
                usage=ModelUsage(),
                model_version="placeholder-v1",
            )

        if self.bedrock_client is None:
            raise RuntimeError("Bedrock client is required when AWS integration is enabled.")

        response = self.bedrock_client.converse(
            modelId=self.config.bedrock_model_id,
            inferenceConfig={
                "maxTokens": 180,
                "temperature": 0,
                "topP": 0.9,
            },
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
        usage = _parse_usage(response.get("usage", {}), config=self.config)
        return BedrockClassificationResult(
            classification=parsed["classification"],
            confidence=parsed["confidence"],
            visible_reasons=parsed["visible_reasons"],
            usage=usage,
            model_version=self.config.bedrock_model_id,
        )


def _classification_prompt() -> str:
    return (
        "You are classifying images for a room-cleanliness workflow. "
        "Return only JSON with keys supported_scene, scene_type, classification, confidence, and visible_reasons. "
        "classification must be one of clean, borderline, dirty. "
        "supported_scene must be true only for a room that housekeeping should evaluate, such as a bedroom, hotel room, bathroom, kitchen, or living room. "
        "Hallways, corridors, offices, and non-room spaces are unsupported and should be classified as borderline. "
        "Use this rubric: "
        "clean means the room is orderly overall; the bed may be lightly rumpled; normal decor, books, toys, or personal items are allowed if the floor is mostly clear and there are no obvious piles of trash or laundry. "
        "borderline means unsupported scene, ambiguous image, or light clutter that does not clearly justify dirty. "
        "dirty means obvious piles of clothes, trash, messy surfaces, significant clutter on the floor, or multiple signs that housekeeping would reject it. "
        "Do not call a room borderline just because it looks lived in. "
        "visible_reasons should be a short array of concrete visual observations."
    )


def _parse_bedrock_payload(payload: str) -> dict[str, object]:
    normalized = payload.strip()
    if normalized.startswith("```"):
        normalized = normalized.strip("`")
        if normalized.startswith("json"):
            normalized = normalized[4:]
        normalized = normalized.strip()

    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise ValueError("Bedrock response did not contain valid JSON.") from exc

    supported_scene = parsed.get("supported_scene")
    classification = ClassificationLabel(parsed["classification"])
    if supported_scene is False:
        classification = ClassificationLabel.BORDERLINE
    confidence = float(parsed["confidence"])
    visible_reasons = [str(item) for item in parsed.get("visible_reasons", [])]
    return {
        "classification": classification,
        "confidence": confidence,
        "visible_reasons": visible_reasons,
    }


def _parse_usage(raw_usage: dict[str, object], *, config: AppConfig) -> ModelUsage:
    input_tokens = int(raw_usage.get("inputTokens", 0) or 0)
    output_tokens = int(raw_usage.get("outputTokens", 0) or 0)
    total_tokens = int(raw_usage.get("totalTokens", input_tokens + output_tokens) or 0)
    estimated_cost_usd = (
        (input_tokens / 1_000_000) * config.bedrock_input_cost_per_million_tokens
        + (output_tokens / 1_000_000) * config.bedrock_output_cost_per_million_tokens
    )
    return ModelUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=round(estimated_cost_usd, 8),
    )
