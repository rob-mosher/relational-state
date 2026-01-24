"""
Promotion Logic

Controls the recursive reflection loop with damped recursion.

Decision Flow (from architecture diagram):
    1. Is this a promotion candidate? (Manual decision)
    2. If yes → Evaluate:
       - Check promotion_depth < MAX_DEPTH
       - Calculate promotion probability: sigmoid(-depth * k)
       - If probability > threshold: ALLOW (append + reprojection)
       - Else: BLOCK (stays ephemeral)
    3. If no → Discard (ephemeral)

Guarantees:
    - Hard depth limit prevents infinite recursion
    - Decay function makes deep promotions increasingly unlikely
    - Explicit decision required (no auto-promotion)
"""

from datetime import datetime
from typing import Optional, Tuple

from relational_domain.canonical_log import append_entry_to_log, generate_entry_id
from relational_domain.context_compiler import sigmoid_decay
from relational_domain.models import DomainConfig, Entry


class PromotionDecision:
    """Result of promotion evaluation"""

    def __init__(
        self,
        allowed: bool,
        reason: str,
        probability: Optional[float] = None,
        new_entry: Optional[Entry] = None,
    ):
        self.allowed = allowed
        self.reason = reason
        self.probability = probability
        self.new_entry = new_entry

    def __repr__(self) -> str:
        if self.allowed:
            return f"PromotionDecision(ALLOWED: {self.reason}, probability={self.probability:.3f})"
        else:
            return f"PromotionDecision(BLOCKED: {self.reason})"


def evaluate_promotion(
    entry: Entry, reason: str, config: Optional[DomainConfig] = None
) -> PromotionDecision:
    """
    Evaluate whether an entry should be promoted

    Args:
        entry: Entry to evaluate for promotion
        reason: Human/AI explanation for why this should be promoted
        config: Configuration (defaults to DomainConfig.from_env())

    Returns:
        PromotionDecision with allowed/blocked and reasoning

    Process:
        1. Check depth < MAX_DEPTH (hard limit)
        2. Calculate promotion probability (sigmoid decay)
        3. If probability > threshold: ALLOW
        4. Else: BLOCK
    """
    config = config or DomainConfig.from_env()

    # Check 1: Hard depth limit
    new_depth = entry.promotion_depth + 1

    if new_depth > config.max_promotion_depth:
        return PromotionDecision(
            allowed=False,
            reason=f"Depth limit reached (current={entry.promotion_depth}, max={config.max_promotion_depth})",
            probability=0.0,
        )

    # Check 2: Calculate promotion probability using sigmoid decay
    # Note: We pass new_depth to sigmoid_decay to predict the weight AFTER promotion
    probability = sigmoid_decay(new_depth, k=config.decay_k)

    if probability < config.promotion_threshold:
        return PromotionDecision(
            allowed=False,
            reason=f"Probability too low ({probability:.3f} < {config.promotion_threshold})",
            probability=probability,
        )

    # Promotion allowed - create new entry
    promoted_entry = create_promoted_entry(entry, reason)

    return PromotionDecision(
        allowed=True,
        reason=f"Promotion allowed (probability={probability:.3f}, new_depth={new_depth})",
        probability=probability,
        new_entry=promoted_entry,
    )


def create_promoted_entry(entry: Entry, reason: str) -> Entry:
    """
    Create a promoted version of an entry

    Args:
        entry: Original entry
        reason: Reason for promotion

    Returns:
        New Entry with incremented depth and promotion metadata
    """
    # Create promotion content
    timestamp = datetime.now()
    timestamp_str = timestamp.strftime("%Y-%m-%d")

    promoted_content = f"""## {timestamp_str}: Promoted Entry - {reason}

**Original Entry ID**: {entry.id[:16]}...
**Original Timestamp**: {entry.timestamp.strftime("%Y-%m-%d %H:%M")}
**Promotion Depth**: {entry.promotion_depth} → {entry.promotion_depth + 1}
**Reason**: {reason}

### Original Content

{entry.content}

---

**Note**: This is a promoted reflection. Promotion depth indicates how many levels
removed this is from the original ephemeral reasoning.
"""

    # Generate new ID for promoted entry
    new_id = generate_entry_id(promoted_content)

    # Create promoted entry
    promoted_entry = Entry(
        id=new_id,
        timestamp=timestamp,
        author=entry.author,
        type="promotion",  # Promoted entries have type "promotion"
        content=promoted_content,
        promotion_depth=entry.promotion_depth + 1,
        trust_weight=entry.trust_weight,  # Inherit trust weight
        metadata={
            "promoted_from": entry.id,
            "promotion_reason": reason,
            "original_timestamp": entry.timestamp.isoformat(),
        },
    )

    return promoted_entry


def promote_and_append(
    entry: Entry, reason: str, config: Optional[DomainConfig] = None, state_dir: Optional[str] = None
) -> Tuple[PromotionDecision, bool]:
    """
    Evaluate promotion and append to canonical log if allowed

    Args:
        entry: Entry to promote
        reason: Reason for promotion
        config: Configuration
        state_dir: State directory (defaults to config.state_dir)

    Returns:
        Tuple of (PromotionDecision, appended: bool)

    Side Effects:
        - If promotion allowed, appends new entry to canonical log
        - Triggers reprojection (caller's responsibility to rebuild vector store)
    """
    config = config or DomainConfig.from_env()
    state_dir = state_dir or config.state_dir

    # Evaluate promotion
    decision = evaluate_promotion(entry, reason, config)

    if not decision.allowed or decision.new_entry is None:
        return (decision, False)

    # Append to canonical log
    try:
        append_entry_to_log(decision.new_entry, state_dir=state_dir)
        return (decision, True)
    except Exception as e:
        # Failed to append
        return (
            PromotionDecision(
                allowed=False,
                reason=f"Failed to append to log: {e}",
                probability=decision.probability,
            ),
            False,
        )


def check_promotion_eligibility(entry: Entry, config: Optional[Config] = None) -> dict:
    """
    Check if an entry is eligible for promotion (without actually promoting)

    Args:
        entry: Entry to check
        config: Configuration

    Returns:
        Dictionary with eligibility info:
            - eligible: bool
            - reason: str
            - probability: float
            - current_depth: int
            - max_depth: int
    """
    config = config or Config.from_env()

    new_depth = entry.promotion_depth + 1
    probability = sigmoid_decay(new_depth, k=config.decay_k)

    eligible = (
        new_depth <= config.max_promotion_depth
        and probability >= config.promotion_threshold
    )

    if not eligible:
        if new_depth > config.max_promotion_depth:
            reason = f"Depth limit reached (current={entry.promotion_depth}, max={config.max_promotion_depth})"
        else:
            reason = f"Probability too low ({probability:.3f} < {config.promotion_threshold})"
    else:
        reason = f"Eligible for promotion (probability={probability:.3f})"

    return {
        "eligible": eligible,
        "reason": reason,
        "probability": probability,
        "current_depth": entry.promotion_depth,
        "new_depth": new_depth,
        "max_depth": config.max_promotion_depth,
        "threshold": config.promotion_threshold,
    }
