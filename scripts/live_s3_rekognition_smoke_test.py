import base64
import os
from pathlib import Path

import boto3

from app.core.config import AppConfig
from app.services.rekognition import RekognitionClient
from app.services.storage import ImageStorageClient

DEFAULT_TEST_IMAGE_PATH = (
    "/System/Library/Image Capture/Automatic Tasks/MakePDF.app/Contents/Resources/horiz.jpg"
)


def main() -> int:
    config = AppConfig(
        aws_integration_enabled=True,
        s3_enabled=True,
        rekognition_enabled=True,
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        s3_bucket_name=os.getenv("S3_BUCKET_NAME", "unset-bucket"),
        minimum_brightness=float(os.getenv("MINIMUM_BRIGHTNESS", "35")),
        minimum_sharpness=float(os.getenv("MINIMUM_SHARPNESS", "25")),
    )
    if config.s3_bucket_name == "unset-bucket":
        raise ValueError("S3_BUCKET_NAME must be set.")

    session = boto3.Session(region_name=config.aws_region)
    storage = ImageStorageClient(config=config, s3_client=session.client("s3"))
    rekognition = RekognitionClient(
        config=config,
        rekognition_client=session.client("rekognition"),
    )

    image_path = Path(os.getenv("TEST_IMAGE_PATH", DEFAULT_TEST_IMAGE_PATH))
    payload = _load_image_as_data_uri(image_path)
    s3_uri = storage.store_inline_image(image_base64=payload)
    quality = rekognition.assess_image_quality(image_reference=s3_uri)

    print(f"Stored image: {s3_uri}")
    print(f"Quality acceptable: {quality.is_acceptable}")
    print(f"Quality reason: {quality.reason}")
    print(f"Retake guidance: {quality.retake_guidance}")
    return 0


def _load_image_as_data_uri(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")
    suffix = path.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        raise ValueError(f"Unsupported test image format: {suffix}")
    content_type = "image/png" if suffix == ".png" else "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


if __name__ == "__main__":
    raise SystemExit(main())
