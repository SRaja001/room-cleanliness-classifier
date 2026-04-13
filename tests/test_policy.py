from app.core.config import AppConfig
from app.models.contracts import (
    ClassificationLabel,
    ImageQualityResult,
    RecommendedAction,
)
from app.services.policy import ReviewPolicy


def test_policy_downgrades_low_confidence_clean_to_borderline() -> None:
    policy = ReviewPolicy(config=AppConfig(clean_confidence_threshold=0.85))

    result = policy.apply(
        initial_label=ClassificationLabel.CLEAN,
        confidence=0.7,
        quality=ImageQualityResult(
            is_acceptable=True,
            reason="ok",
            retake_guidance="None.",
        ),
    )

    assert result["classification"] == ClassificationLabel.BORDERLINE
    assert result["recommended_action"] == RecommendedAction.ESCALATE
    assert result["needs_review"] is True


def test_policy_marks_bad_quality_for_retake() -> None:
    policy = ReviewPolicy(config=AppConfig(clean_confidence_threshold=0.85))

    result = policy.apply(
        initial_label=ClassificationLabel.DIRTY,
        confidence=0.92,
        quality=ImageQualityResult(
            is_acceptable=False,
            reason="too dark",
            retake_guidance="Retake in better lighting.",
        ),
    )

    assert result["classification"] == ClassificationLabel.BORDERLINE
    assert result["recommended_action"] == RecommendedAction.RETAKE
    assert result["confidence"] == 0.3
