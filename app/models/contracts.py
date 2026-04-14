from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ImageRole(str, Enum):
    AFTER = "after"
    BEFORE = "before"


class ClassificationLabel(str, Enum):
    CLEAN = "clean"
    BORDERLINE = "borderline"
    DIRTY = "dirty"


class RecommendedAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    RETAKE = "retake"
    ESCALATE = "escalate"


class HealthResponse(BaseModel):
    status: str
    app_name: str


class ClassifyRoomRequest(BaseModel):
    image_base64: str | None = Field(
        default=None,
        description="Base64-encoded image payload for early testing.",
    )
    image_s3_uri: str | None = Field(
        default=None,
        description="Private S3 URI for later upload flows.",
    )
    image_role: ImageRole = ImageRole.AFTER
    room_type: str | None = None
    source: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "image_base64": "cGxhY2Vob2xkZXI=",
                    "image_role": "after",
                    "room_type": "bedroom",
                    "source": "manual-test",
                }
            ]
        }
    )

    @model_validator(mode="after")
    def validate_image_reference(self) -> "ClassifyRoomRequest":
        if not self.image_base64 and not self.image_s3_uri:
            raise ValueError("Either image_base64 or image_s3_uri must be provided.")
        return self


class ImageQualityResult(BaseModel):
    is_acceptable: bool
    reason: str
    retake_guidance: str


class ModelUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)


class ClassifyRoomResponse(BaseModel):
    prediction_id: str
    classification: ClassificationLabel
    confidence: float = Field(ge=0.0, le=1.0)
    needs_review: bool
    recommended_action: RecommendedAction
    visible_reasons: list[str]
    image_quality: ImageQualityResult
    model_version: str
    model_usage: ModelUsage


class AdminReviewRequest(BaseModel):
    final_classification: ClassificationLabel
    admin_comment: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)


class AdminReviewResponse(BaseModel):
    prediction_id: str
    final_classification: ClassificationLabel
    admin_comment: str
    reviewer: str
