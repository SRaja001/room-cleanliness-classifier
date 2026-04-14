import base64
import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.api import create_app
from app.core.config import AppConfig


def main() -> int:
    image_path = os.getenv("TEST_IMAGE_PATH")
    if not image_path:
        raise ValueError("TEST_IMAGE_PATH must be set.")

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    config = AppConfig(
        aws_integration_enabled=True,
        s3_enabled=True,
        rekognition_enabled=True,
        bedrock_enabled=False,
        dynamodb_enabled=True,
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        s3_bucket_name=os.getenv("S3_BUCKET_NAME", "unset-bucket"),
        dynamodb_table_name=os.getenv(
            "DYNAMODB_TABLE_NAME", "room-cleanliness-predictions-dev"
        ),
        minimum_brightness=float(os.getenv("MINIMUM_BRIGHTNESS", "35")),
        minimum_sharpness=float(os.getenv("MINIMUM_SHARPNESS", "25")),
    )
    if config.s3_bucket_name == "unset-bucket":
        raise ValueError("S3_BUCKET_NAME must be set.")
    client = TestClient(create_app(config=config))

    response = client.post(
        "/classify",
        json={
            "image_base64": _load_image_as_data_uri(path),
            "image_role": "after",
            "room_type": "bedroom",
            "source": "live-local-image-test",
        },
    )
    body = response.json()

    print(f"HTTP status: {response.status_code}")
    print(f"Prediction ID: {body.get('prediction_id')}")
    print(f"Classification: {body.get('classification')}")
    print(f"Confidence: {body.get('confidence')}")
    print(f"Needs review: {body.get('needs_review')}")
    print(f"Recommended action: {body.get('recommended_action')}")
    print(f"Image quality: {body.get('image_quality')}")
    print(f"Visible reasons: {body.get('visible_reasons')}")
    return 0


def _load_image_as_data_uri(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        raise ValueError(f"Unsupported image format: {suffix}")
    content_type = "image/png" if suffix == ".png" else "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


if __name__ == "__main__":
    raise SystemExit(main())
