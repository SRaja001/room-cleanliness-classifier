import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import boto3
from fastapi.testclient import TestClient

from app.api import create_app
from app.core.config import AppConfig


@dataclass(frozen=True)
class ExistingS3Sample:
    label: str
    source_s3_uri: str
    target_key: str


@dataclass(frozen=True)
class LocalImageSample:
    label: str
    source_path: Path
    target_key: str


def main() -> int:
    bucket_name = os.getenv("S3_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME must be set.")

    region = os.getenv("AWS_REGION", "us-east-1")
    model_id = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
    dynamodb_table_name = os.getenv(
        "DYNAMODB_TABLE_NAME", "room-cleanliness-predictions-dev"
    )
    dirty_source_uri = os.getenv(
        "DIRTY_SOURCE_S3_URI",
        "s3://room-cleanliness-classifier-dev-443658108558/uploads/8da1b8eb-e23c-4f5d-8d34-1a4e2854d85c.jpg",
    )

    existing_samples = [
        ExistingS3Sample(
            label="dirty_room_existing",
            source_s3_uri=dirty_source_uri,
            target_key="named-tests/dirty-room-bedroom.jpg",
        )
    ]
    local_samples = [
        LocalImageSample(
            label="hallway_not_room",
            source_path=Path("/Users/sreeneshraja/Downloads/Hall-way.webp"),
            target_key="named-tests/hallway-not-room.jpg",
        ),
        LocalImageSample(
            label="clean_room",
            source_path=Path(
                "/Users/sreeneshraja/Downloads/af69fd4de79fd43e958839dc2d241b76965e650d.webp"
            ),
            target_key="named-tests/clean-room-bedroom.jpg",
        ),
    ]

    s3_client = boto3.client("s3", region_name=region)
    session = boto3.Session(region_name=region)

    named_uris: dict[str, str] = {}
    for sample in existing_samples:
        named_uris[sample.label] = _copy_named_object(
            s3_client=s3_client,
            bucket_name=bucket_name,
            sample=sample,
        )
    for sample in local_samples:
        named_uris[sample.label] = _upload_named_local_image(
            s3_client=s3_client,
            bucket_name=bucket_name,
            sample=sample,
        )

    config = AppConfig(
        aws_integration_enabled=True,
        s3_enabled=True,
        rekognition_enabled=True,
        bedrock_enabled=True,
        dynamodb_enabled=True,
        aws_region=region,
        s3_bucket_name=bucket_name,
        dynamodb_table_name=dynamodb_table_name,
        bedrock_model_id=model_id,
        bedrock_input_cost_per_million_tokens=float(
            os.getenv("BEDROCK_INPUT_COST_PER_MILLION_TOKENS", "0.06")
        ),
        bedrock_output_cost_per_million_tokens=float(
            os.getenv("BEDROCK_OUTPUT_COST_PER_MILLION_TOKENS", "0.24")
        ),
        minimum_brightness=float(os.getenv("MINIMUM_BRIGHTNESS", "35")),
        minimum_sharpness=float(os.getenv("MINIMUM_SHARPNESS", "25")),
    )
    client = TestClient(create_app(config=config))

    results: list[dict[str, object]] = []
    for label, s3_uri in named_uris.items():
        response = client.post(
            "/classify",
            json={
                "image_s3_uri": s3_uri,
                "image_role": "after",
                "source": "named-test-batch",
            },
        )
        body = response.json()
        results.append(
            {
                "label": label,
                "s3_uri": s3_uri,
                "status_code": response.status_code,
                "prediction_id": body.get("prediction_id"),
                "classification": body.get("classification"),
                "confidence": body.get("confidence"),
                "needs_review": body.get("needs_review"),
                "recommended_action": body.get("recommended_action"),
                "image_quality": body.get("image_quality"),
                "visible_reasons": body.get("visible_reasons"),
                "model_version": body.get("model_version"),
                "model_usage": body.get("model_usage"),
            }
        )

    print(json.dumps(results, indent=2))
    return 0


def _copy_named_object(
    *, s3_client: object, bucket_name: str, sample: ExistingS3Sample
) -> str:
    source_bucket, source_key = _parse_s3_uri(sample.source_s3_uri)
    s3_client.copy_object(
        Bucket=bucket_name,
        Key=sample.target_key,
        CopySource={"Bucket": source_bucket, "Key": source_key},
        ContentType="image/jpeg",
        MetadataDirective="REPLACE",
        ServerSideEncryption="AES256",
    )
    return f"s3://{bucket_name}/{sample.target_key}"


def _upload_named_local_image(
    *, s3_client: object, bucket_name: str, sample: LocalImageSample
) -> str:
    if not sample.source_path.exists():
        raise FileNotFoundError(f"Image not found: {sample.source_path}")

    converted_path = _convert_to_jpeg(sample.source_path)
    try:
        s3_client.upload_file(
            str(converted_path),
            bucket_name,
            sample.target_key,
            ExtraArgs={
                "ContentType": "image/jpeg",
                "ServerSideEncryption": "AES256",
            },
        )
    finally:
        converted_path.unlink(missing_ok=True)
    return f"s3://{bucket_name}/{sample.target_key}"


def _convert_to_jpeg(source_path: Path) -> Path:
    fd, output_path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    output_file = Path(output_path)
    subprocess.run(
        ["sips", "-s", "format", "jpeg", str(source_path), "--out", str(output_file)],
        check=True,
        capture_output=True,
        text=True,
    )
    return output_file


def _parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    bucket_and_key = s3_uri.removeprefix("s3://")
    bucket, _, key = bucket_and_key.partition("/")
    if not bucket or not key:
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    return bucket, key


if __name__ == "__main__":
    raise SystemExit(main())
