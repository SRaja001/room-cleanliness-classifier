from app.core.config import AppConfig
from app.models.contracts import (
    ClassificationLabel,
    ImageQualityResult,
    RecommendedAction,
)


class ReviewPolicy:
    """Conservative MVP policy to avoid a false clean result."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or AppConfig.from_env()

    def apply(
        self,
        *,
        initial_label: ClassificationLabel,
        confidence: float,
        quality: ImageQualityResult,
    ) -> dict[str, object]:
        if not quality.is_acceptable:
            return {
                "classification": ClassificationLabel.BORDERLINE,
                "confidence": min(confidence, 0.3),
                "needs_review": True,
                "recommended_action": RecommendedAction.RETAKE,
            }

        if (
            initial_label == ClassificationLabel.CLEAN
            and confidence < self.config.clean_confidence_threshold
        ):
            return {
                "classification": ClassificationLabel.BORDERLINE,
                "confidence": confidence,
                "needs_review": True,
                "recommended_action": RecommendedAction.ESCALATE,
            }

        action = (
            RecommendedAction.APPROVE
            if initial_label == ClassificationLabel.CLEAN
            else RecommendedAction.REJECT
            if initial_label == ClassificationLabel.DIRTY
            else RecommendedAction.ESCALATE
        )
        return {
            "classification": initial_label,
            "confidence": confidence,
            "needs_review": True,
            "recommended_action": action,
        }
