import os

from pydantic import BaseModel, ConfigDict


class AppConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_name: str = "room-cleanliness-classifier"
    app_version: str = "0.1.0"
    environment: str = "development"
    aws_region: str = "us-east-1"
    aws_integration_enabled: bool = False
    s3_enabled: bool = False
    rekognition_enabled: bool = False
    bedrock_enabled: bool = False
    dynamodb_enabled: bool = False
    s3_bucket_name: str = "room-cleanliness-classifier-dev"
    s3_key_prefix: str = "uploads"
    dynamodb_table_name: str = "room-cleanliness-predictions-dev"
    bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    clean_confidence_threshold: float = 0.85
    minimum_brightness: float = 35.0
    minimum_sharpness: float = 25.0

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            app_name=os.getenv("APP_NAME", cls.model_fields["app_name"].default),
            app_version=os.getenv("APP_VERSION", cls.model_fields["app_version"].default),
            environment=os.getenv("APP_ENV", cls.model_fields["environment"].default),
            aws_region=os.getenv("AWS_REGION", cls.model_fields["aws_region"].default),
            aws_integration_enabled=_read_bool(
                os.getenv("AWS_INTEGRATION_ENABLED"),
                default=cls.model_fields["aws_integration_enabled"].default,
            ),
            s3_enabled=_read_bool(
                os.getenv("S3_ENABLED"),
                default=cls.model_fields["s3_enabled"].default,
            ),
            rekognition_enabled=_read_bool(
                os.getenv("REKOGNITION_ENABLED"),
                default=cls.model_fields["rekognition_enabled"].default,
            ),
            bedrock_enabled=_read_bool(
                os.getenv("BEDROCK_ENABLED"),
                default=cls.model_fields["bedrock_enabled"].default,
            ),
            dynamodb_enabled=_read_bool(
                os.getenv("DYNAMODB_ENABLED"),
                default=cls.model_fields["dynamodb_enabled"].default,
            ),
            s3_bucket_name=os.getenv(
                "S3_BUCKET_NAME", cls.model_fields["s3_bucket_name"].default
            ),
            s3_key_prefix=os.getenv(
                "S3_KEY_PREFIX", cls.model_fields["s3_key_prefix"].default
            ),
            dynamodb_table_name=os.getenv(
                "DYNAMODB_TABLE_NAME",
                cls.model_fields["dynamodb_table_name"].default,
            ),
            bedrock_model_id=os.getenv(
                "BEDROCK_MODEL_ID", cls.model_fields["bedrock_model_id"].default
            ),
            clean_confidence_threshold=float(
                os.getenv(
                    "CLEAN_CONFIDENCE_THRESHOLD",
                    cls.model_fields["clean_confidence_threshold"].default,
                )
            ),
            minimum_brightness=float(
                os.getenv(
                    "MINIMUM_BRIGHTNESS",
                    cls.model_fields["minimum_brightness"].default,
                )
            ),
            minimum_sharpness=float(
                os.getenv(
                    "MINIMUM_SHARPNESS",
                    cls.model_fields["minimum_sharpness"].default,
                )
            ),
        )


def _read_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
