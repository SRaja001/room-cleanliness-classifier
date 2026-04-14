import json
from dataclasses import dataclass

import boto3

from app.core.config import AppConfig
from app.models.contracts import ClassificationLabel
from app.services.storage import ImageStorageClient


@dataclass(frozen=True)
class Sample:
    label: str
    s3_uri: str
    expected: ClassificationLabel


@dataclass(frozen=True)
class Experiment:
    name: str
    model_id: str
    prompt: str
    two_stage: bool


SAMPLES = [
    Sample(
        label="dirty_room_existing",
        s3_uri="s3://room-cleanliness-classifier-dev-443658108558/named-tests/dirty-room-bedroom.jpg",
        expected=ClassificationLabel.DIRTY,
    ),
    Sample(
        label="hallway_not_room",
        s3_uri="s3://room-cleanliness-classifier-dev-443658108558/named-tests/hallway-not-room.jpg",
        expected=ClassificationLabel.BORDERLINE,
    ),
    Sample(
        label="clean_room",
        s3_uri="s3://room-cleanliness-classifier-dev-443658108558/named-tests/clean-room-bedroom.jpg",
        expected=ClassificationLabel.CLEAN,
    ),
]


EXPERIMENTS = [
    Experiment(
        name="option_1_tuned_prompt_writer",
        model_id="writer.palmyra-vision-7b",
        prompt=(
            "You are classifying images for a room-cleanliness workflow.\n"
            "Return only JSON with keys supported_scene, scene_type, classification, confidence, visible_reasons.\n"
            "classification must be one of clean, borderline, dirty.\n"
            "supported_scene must be true only for a room that housekeeping should evaluate, such as a bedroom, hotel room, bathroom, kitchen, or living room.\n"
            "Hallways, corridors, offices, and non-room spaces are unsupported and should be classified as borderline.\n"
            "Use this rubric:\n"
            "- clean: room is orderly overall; bed may be lightly rumpled; normal decor, books, toys, or personal items are allowed if the floor is mostly clear and there are no obvious piles of trash or laundry.\n"
            "- borderline: unsupported scene, ambiguous image, or light clutter that does not clearly justify dirty.\n"
            "- dirty: obvious piles of clothes, trash, messy surfaces, significant clutter on the floor, or multiple signs that housekeeping would reject it.\n"
            "Do not call a room borderline just because it looks lived in.\n"
            "visible_reasons should be short concrete observations."
        ),
        two_stage=False,
    ),
    Experiment(
        name="option_2_nova_lite_tuned_prompt",
        model_id="amazon.nova-lite-v1:0",
        prompt=(
            "You are classifying images for a room-cleanliness workflow.\n"
            "Return only JSON with keys supported_scene, scene_type, classification, confidence, visible_reasons.\n"
            "classification must be one of clean, borderline, dirty.\n"
            "supported_scene must be true only for a room that housekeeping should evaluate, such as a bedroom, hotel room, bathroom, kitchen, or living room.\n"
            "Hallways, corridors, offices, and non-room spaces are unsupported and should be classified as borderline.\n"
            "Use this rubric:\n"
            "- clean: room is orderly overall; bed may be lightly rumpled; normal decor, books, toys, or personal items are allowed if the floor is mostly clear and there are no obvious piles of trash or laundry.\n"
            "- borderline: unsupported scene, ambiguous image, or light clutter that does not clearly justify dirty.\n"
            "- dirty: obvious piles of clothes, trash, messy surfaces, significant clutter on the floor, or multiple signs that housekeeping would reject it.\n"
            "Do not call a room borderline just because it looks lived in.\n"
            "visible_reasons should be short concrete observations."
        ),
        two_stage=False,
    ),
    Experiment(
        name="option_3_two_stage_hybrid_nova_lite",
        model_id="amazon.nova-lite-v1:0",
        prompt=(
            "You are analyzing an image for a room-cleanliness workflow.\n"
            "Return only JSON with keys scene_type, supported_scene, severe_issues, moderate_issues, minor_issues, cleanliness_score.\n"
            "scene_type should describe the space, such as bedroom, bathroom, hallway, kitchen, living_room, or other.\n"
            "supported_scene should be true only for spaces housekeeping should score, such as bedroom, hotel room, bathroom, kitchen, or living room.\n"
            "Hallways, corridors, offices, and non-room spaces must be marked supported_scene=false.\n"
            "severe_issues should contain only obvious reject-level cleanliness issues such as piles of clothes, visible trash, many dirty surfaces, or severe floor clutter.\n"
            "moderate_issues should contain issues that are noticeable but may not justify rejection by themselves.\n"
            "minor_issues should contain harmless lived-in details.\n"
            "cleanliness_score should be an integer from 0 to 100, where 100 is very clean.\n"
            "A neatly kept room with small personal items, a lightly rumpled bed, books, wall decor, or a tidy desk can still be clean."
        ),
        two_stage=True,
    ),
]


def main() -> int:
    session = boto3.Session(region_name="us-east-1")
    bedrock = session.client("bedrock-runtime")
    storage = ImageStorageClient(
        config=AppConfig(
            aws_integration_enabled=True,
            s3_enabled=True,
            aws_region="us-east-1",
            s3_bucket_name="room-cleanliness-classifier-dev-443658108558",
        ),
        s3_client=session.client("s3"),
    )

    results: list[dict[str, object]] = []
    for experiment in EXPERIMENTS:
        experiment_results = []
        correct = 0
        total_input_tokens = 0
        total_output_tokens = 0
        for sample in SAMPLES:
            result = _invoke_model(
                bedrock=bedrock,
                storage=storage,
                sample=sample,
                experiment=experiment,
            )
            if result["final_classification"] == sample.expected.value:
                correct += 1
            total_input_tokens += result["usage"]["inputTokens"]
            total_output_tokens += result["usage"]["outputTokens"]
            experiment_results.append(result)

        results.append(
            {
                "experiment": experiment.name,
                "model_id": experiment.model_id,
                "correct": correct,
                "total": len(SAMPLES),
                "accuracy": round(correct / len(SAMPLES), 2),
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "samples": experiment_results,
            }
        )

    print(json.dumps(results, indent=2))
    return 0


def _invoke_model(*, bedrock: object, storage: ImageStorageClient, sample: Sample, experiment: Experiment) -> dict[str, object]:
    response = bedrock.converse(
        modelId=experiment.model_id,
        inferenceConfig={"maxTokens": 220, "temperature": 0, "topP": 0.9},
        messages=[
            {
                "role": "user",
                "content": [
                    {"text": experiment.prompt},
                    {
                        "image": {
                            "format": storage.infer_image_format(image_s3_uri=sample.s3_uri),
                            "source": {
                                "bytes": storage.load_image_bytes(image_s3_uri=sample.s3_uri)
                            },
                        }
                    },
                ],
            }
        ],
    )
    content = response.get("output", {}).get("message", {}).get("content", [])
    raw_text = "".join(block.get("text", "") for block in content if "text" in block)
    payload = _parse_json(raw_text)

    if experiment.two_stage:
        final_classification = _apply_hybrid_mapping(payload)
        visible_reasons = (
            payload.get("severe_issues", [])
            + payload.get("moderate_issues", [])
            + payload.get("minor_issues", [])
        )[:6]
        confidence = _score_confidence(payload, final_classification)
    else:
        final_classification = payload["classification"]
        visible_reasons = payload.get("visible_reasons", [])
        confidence = payload["confidence"]

    return {
        "label": sample.label,
        "expected": sample.expected.value,
        "final_classification": final_classification,
        "confidence": confidence,
        "visible_reasons": visible_reasons,
        "raw_payload": payload,
        "usage": response.get("usage", {}),
    }


def _parse_json(payload: str) -> dict[str, object]:
    normalized = payload.strip()
    if normalized.startswith("```"):
        normalized = normalized.strip("`")
        if normalized.startswith("json"):
            normalized = normalized[4:]
        normalized = normalized.strip()
    return json.loads(normalized)


def _apply_hybrid_mapping(payload: dict[str, object]) -> str:
    supported_scene = bool(payload.get("supported_scene", False))
    severe_issues = payload.get("severe_issues", []) or []
    moderate_issues = payload.get("moderate_issues", []) or []
    cleanliness_score = int(payload.get("cleanliness_score", 0) or 0)
    if not supported_scene:
        return ClassificationLabel.BORDERLINE.value
    if len(severe_issues) > 0:
        return ClassificationLabel.DIRTY.value
    if cleanliness_score >= 85 and len(moderate_issues) == 0:
        return ClassificationLabel.CLEAN.value
    return ClassificationLabel.BORDERLINE.value


def _score_confidence(payload: dict[str, object], final_classification: str) -> float:
    supported_scene = bool(payload.get("supported_scene", False))
    cleanliness_score = int(payload.get("cleanliness_score", 0) or 0)
    severe_count = len(payload.get("severe_issues", []) or [])
    moderate_count = len(payload.get("moderate_issues", []) or [])
    if not supported_scene:
        return 0.85
    if final_classification == ClassificationLabel.DIRTY.value:
        return min(0.98, 0.75 + (0.08 * severe_count))
    if final_classification == ClassificationLabel.CLEAN.value:
        return min(0.95, max(0.8, cleanliness_score / 100))
    return max(0.6, 0.8 - (0.05 * moderate_count))


if __name__ == "__main__":
    raise SystemExit(main())
