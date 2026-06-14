"""
Decision Engine — maps image authenticity + ML risk → final action.
"""
from utils.logger import get_logger

logger = get_logger(__name__)

# Action constants
ACTION_PROCEED        = "PROCEED"
ACTION_SEND_AGENT     = "SEND_AGENT"
ACTION_ASK_VIDEO      = "ASK_VIDEO"
ACTION_CUSTOMER_CARE  = "CUSTOMER_CARE"
ACTION_MONITORING     = "MONITORING"
ACTION_MANUAL_REVIEW  = "MANUAL_REVIEW"


def decide(
    image_status: str,          # AUTHENTIC | SUSPICIOUS | FAKE | UNKNOWN
    image_confidence: float,
    risk_level: str,            # LOW | MEDIUM | HIGH
    risk_score: float,
    return_type: str,           # "return" | "returnless"
) -> dict:
    """
    Core decision logic — returns action + human-readable reason.
    """

    logger.info(
        f"Decision input → image_status={image_status}, confidence={image_confidence}, "
        f"risk_level={risk_level}, risk_score={risk_score}, return_type={return_type}"
    )

    action = ACTION_PROCEED
    reason = ""
    severity = "LOW"

    if image_status in ("FAKE", "SUSPICIOUS"):
        severity = "HIGH" if image_status == "FAKE" else "MEDIUM"

        if return_type == "return":
            action = ACTION_SEND_AGENT
            reason = (
                f"Image flagged as {image_status} (confidence {image_confidence:.0%}). "
                "Physical return request requires agent verification before approval."
            )
        else:  # returnless
            action = ACTION_ASK_VIDEO
            reason = (
                f"Image flagged as {image_status} (confidence {image_confidence:.0%}) "
                "for a returnless request. Customer must submit a short video for validation. "
                "Escalate to Customer Care if video is inconclusive."
            )

    elif image_status == "AUTHENTIC":
        if risk_level == "HIGH":
            action = ACTION_MONITORING
            severity = "MEDIUM"
            reason = (
                f"Image is AUTHENTIC but ML risk score is high ({risk_score:.0%}). "
                "Return is approved with enhanced account monitoring flagged."
            )
        else:
            action = ACTION_PROCEED
            severity = "LOW"
            reason = (
                f"Image AUTHENTIC (confidence {image_confidence:.0%}) and ML risk is {risk_level}. "
                "Return approved — no further action required."
            )

    else:  # UNKNOWN — API error fallback
        severity = risk_level  # Use the ML risk level as the severity

        if risk_level == "HIGH":
            action = ACTION_MANUAL_REVIEW
            reason = (
                "Image authenticity could not be determined (API error). "
                "ML risk is HIGH — routing to manual review."
            )
        else:
            action = ACTION_SEND_AGENT
            reason = (
                f"Image authenticity could not be determined (API error). "
                f"ML risk is {risk_level} — routing to agent for routine image check."
            )

    result = {
        "action": action,
        "reason": reason,
        "severity": severity,
    }
    logger.info(f"Decision output → {result}")
    return result


def map_image_status(is_deepfake: bool | None, confidence: float | None) -> str:
    """
    Maps Hive AI output → image status label.
    is_deepfake = True when fake_score >= 5%
    """
    if is_deepfake is None or confidence is None:
        return "UNKNOWN"

    if is_deepfake:
        if confidence >= 0.40:   # 40%+ fake signal → definitely FAKE
            return "FAKE"
        if confidence >= 0.10:   # 10-40% → SUSPICIOUS
            return "SUSPICIOUS"
        return "SUSPICIOUS"      # even 5-10% → flag as SUSPICIOUS
    else:
        if confidence >= 0.90:   # 90%+ real → AUTHENTIC
            return "AUTHENTIC"
        return "SUSPICIOUS"      # anything less → SUSPICIOUS
