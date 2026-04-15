import base64
import json
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
        bedrock_enabled=os.getenv("BEDROCK_ENABLED", "true").lower() == "true",
        dynamodb_enabled=True,
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        s3_bucket_name=os.getenv("S3_BUCKET_NAME", "unset-bucket"),
        dynamodb_table_name=os.getenv(
            "DYNAMODB_TABLE_NAME", "room-cleanliness-predictions-dev"
        ),
        bedrock_model_id=os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0"),
        bedrock_input_cost_per_million_tokens=float(
            os.getenv("BEDROCK_INPUT_COST_PER_MILLION_TOKENS", "0.06")
        ),
        bedrock_output_cost_per_million_tokens=float(
            os.getenv("BEDROCK_OUTPUT_COST_PER_MILLION_TOKENS", "0.24")
        ),
    )
    if config.s3_bucket_name == "unset-bucket":
        raise ValueError("S3_BUCKET_NAME must be set.")

    client = TestClient(create_app(config=config))
    classify_response = client.post(
        "/classify",
        json={
            "image_base64": _load_image_as_data_uri(path),
            "image_role": "after",
            "room_type": "bedroom",
            "source": "live-review-reporting-test",
        },
    )
    classify_response.raise_for_status()
    prediction = classify_response.json()
    prediction_id = prediction["prediction_id"]

    fetched = client.get(f"/predictions/{prediction_id}")
    fetched.raise_for_status()

    listed = client.get("/predictions", params={"limit": 5})
    listed.raise_for_status()

    summary_before = client.get("/reports/summary")
    summary_before.raise_for_status()

    review = client.post(
        f"/predictions/{prediction_id}/review",
        json={
            "final_classification": prediction["classification"],
            "admin_comment": "Smoke test review saved successfully.",
            "reviewer": "codex-smoke-test",
        },
    )
    review.raise_for_status()

    summary_after = client.get("/reports/summary")
    summary_after.raise_for_status()

    print(
        json.dumps(
            {
                "classification": prediction,
                "fetched_prediction": fetched.json(),
                "prediction_list": listed.json(),
                "summary_before_review": summary_before.json(),
                "saved_review": review.json(),
                "summary_after_review": summary_after.json(),
            },
            indent=2,
        )
    )
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
