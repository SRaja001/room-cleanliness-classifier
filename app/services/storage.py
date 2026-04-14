import base64
import binascii
import uuid
from urllib.parse import urlparse

from app.core.config import AppConfig


class ImageStorageClient:
    """Storage abstraction for inline image testing and future S3 integration."""

    def __init__(self, *, config: AppConfig, s3_client: object | None = None) -> None:
        self.config = config
        self.s3_client = s3_client

    def store_inline_image(self, *, image_base64: str) -> str:
        image_bytes = decode_base64_image(image_base64)
        extension = infer_image_extension(image_base64)
        content_type = infer_content_type(image_base64)
        object_key = f"{self.config.s3_key_prefix}/{uuid.uuid4()}.{extension}"
        s3_uri = f"s3://{self.config.s3_bucket_name}/{object_key}"
        if not (self.config.aws_integration_enabled and self.config.s3_enabled):
            return s3_uri

        if self.s3_client is None:
            raise RuntimeError("S3 client is required when AWS integration is enabled.")

        self.s3_client.put_object(
            Bucket=self.config.s3_bucket_name,
            Key=object_key,
            Body=image_bytes,
            ContentType=content_type,
        )
        return s3_uri

    def load_image_bytes(self, *, image_s3_uri: str) -> bytes:
        if self.s3_client is None:
            raise RuntimeError("S3 client is required to load image bytes.")

        bucket, key = parse_s3_uri(image_s3_uri)
        response = self.s3_client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()

    def infer_image_format(self, *, image_s3_uri: str) -> str:
        _, key = parse_s3_uri(image_s3_uri)
        if key.lower().endswith(".png"):
            return "png"
        return "jpeg"


def decode_base64_image(payload: str) -> bytes:
    _, _, encoded = payload.partition(",")
    candidate = encoded or payload
    try:
        return base64.b64decode(candidate, validate=True)
    except binascii.Error as exc:
        raise ValueError("image_base64 must contain valid base64-encoded image data.") from exc


def infer_content_type(payload: str) -> str:
    header, _, _ = payload.partition(",")
    if "image/png" in header:
        return "image/png"
    return "image/jpeg"


def infer_image_extension(payload: str) -> str:
    return "png" if infer_content_type(payload) == "image/png" else "jpg"


def parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    parsed = urlparse(s3_uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path:
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    return parsed.netloc, parsed.path.lstrip("/")
