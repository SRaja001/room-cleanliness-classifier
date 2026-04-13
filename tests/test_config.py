import os

from app.core.config import AppConfig


def test_app_config_reads_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "cleanliness-service")
    monkeypatch.setenv("APP_VERSION", "0.2.0")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("AWS_INTEGRATION_ENABLED", "true")
    monkeypatch.setenv("S3_ENABLED", "true")
    monkeypatch.setenv("REKOGNITION_ENABLED", "true")
    monkeypatch.setenv("BEDROCK_ENABLED", "false")
    monkeypatch.setenv("DYNAMODB_ENABLED", "true")
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("S3_KEY_PREFIX", "incoming")
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "predictions-test")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "test-model")
    monkeypatch.setenv("CLEAN_CONFIDENCE_THRESHOLD", "0.91")
    monkeypatch.setenv("MINIMUM_BRIGHTNESS", "40")
    monkeypatch.setenv("MINIMUM_SHARPNESS", "30")

    config = AppConfig.from_env()

    assert config.app_name == "cleanliness-service"
    assert config.app_version == "0.2.0"
    assert config.environment == "test"
    assert config.aws_region == "us-west-2"
    assert config.aws_integration_enabled is True
    assert config.s3_enabled is True
    assert config.rekognition_enabled is True
    assert config.bedrock_enabled is False
    assert config.dynamodb_enabled is True
    assert config.s3_bucket_name == "test-bucket"
    assert config.s3_key_prefix == "incoming"
    assert config.dynamodb_table_name == "predictions-test"
    assert config.bedrock_model_id == "test-model"
    assert config.clean_confidence_threshold == 0.91
    assert config.minimum_brightness == 40.0
    assert config.minimum_sharpness == 30.0
