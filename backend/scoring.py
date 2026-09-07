import re
from typing import Any


# ============================================================
# THREAT CONFIGURATION
# ============================================================

THREAT_CONFIG = {
    "urgency": {
        "label": "Urgency",
        "weight": 20,
        "severity": "high",
    },

    "scarcity": {
        "label": "Scarcity",
        "weight": 18,
        "severity": "high",
    },

    "social_proof": {
        "label": "Social Proof",
        "weight": 12,
        "severity": "medium",
    },

    "misdirection": {
        "label": "Misdirection",
        "weight": 18,
        "severity": "high",
    },

    "obstruction": {
        "label": "Obstruction",
        "weight": 10,
        "severity": "medium",
    },

    "sneaking": {
        "label": "Sneaking",
        "weight": 12,
        "severity": "high",
    },

    "forced_action": {
        "label": "Forced Action",
        "weight": 10,
        "severity": "high",
    },
}


# ============================================================
# HEURISTIC PATTERNS
# ============================================================

PATTERNS = {

    "urgency": [
        r"\bhurry\b",
        r"\bact\s+now\b",
        r"\blimited[- ]time\b",
        r"\blimited[- ]time\s+(?:deal|offer)\b",
        r"\blast\s+chance\b",
        r"\bdeal\s+ends\b",
        r"\bends?\s+(?:today|tonight|soon)\b",
        r"\bexpires?\s+(?:today|tonight|soon)\b",
        r"\bcountdown\b",
        r"\bflash\s+sale\b",
        r"\bfinal\s+hours?\b",
        r"\bonly\s+\d+\s*(?:minutes?|hours?)\b",
    ],

    "scarcity": [
    r"\bonly\s+\d+\s+(?:item|items|unit|units|product|products)\s+(?:left|remaining|available)\b",
    r"\bonly\s+\d+\s+left\b",
    r"\bonly\s+\d+\s+remaining\b",
    r"\bonly\s+\d+\s+available\b",
    r"\blow\s+stock\b",
    r"\blimited\s+(?:stock|quantity|availability)\b",
    r"\bselling\s+fast\b",
    r"\b\d+\s+(?:items?|units?)\s+left\b",
    r"\blast\s+\d+\s+(?:items?|units?)\b",
    ],

    "social_proof": [
        r"\b\d+\s+(?:people|customers|users)\s+(?:are\s+)?(?:viewing|watching)\b",
        r"\b\d+\s+(?:people|customers)\s+(?:bought|purchased)\b",
        r"\b\d+\s+sold\b",
        r"\bbestseller\b",
        r"\bpopular\s+(?:choice|item|product)\b",
        r"\btrending\b",
        r"\bpeople\s+are\s+viewing\b",
        r"\bjoin\s+\d+.*(?:customers|users)\b",
    ],

    "misdirection": [
        r"\b\d{1,3}%\s*off\b",
        r"\bwas\s+(?:₹|rs\.?|\$|€|£)?\s*\d[\d,]*(?:\.\d{1,2})?\b",
        r"\bnow\s+(?:₹|rs\.?|\$|€|£)?\s*\d[\d,]*(?:\.\d{1,2})?\b",
        r"\bsave\s+(?:₹|rs\.?|\$|€|£)?\s*\d[\d,]*(?:\.\d{1,2})?\b",
        r"\bcompare\s+at\b",
        r"\blist\s+price\b",
        r"\bmarked\s+down\b",
        r"\brrp\b",
        r"\bfrom\s+(?:₹|rs\.?|\$|€|£)?\s*\d[\d,]*(?:\.\d{1,2})?\b",
    ],

    "obstruction": [
        r"\bcontact\s+support\s+to\s+cancel\b",
        r"\bcall\s+(?:us|support)\s+to\s+cancel\b",
        r"\bcannot\s+cancel\s+online\b",
        r"\bcannot\s+cancel\b",
        r"\bmust\s+contact\s+support\b",
        r"\bcancellation\s+requires\b",
        r"\bverification\s+required\s+to\s+cancel\b",
    ],

    "sneaking": [
        r"\bservice\s+fee\b",
        r"\bprocessing\s+fee\b",
        r"\bhandling\s+fee\b",
        r"\bplatform\s+fee\b",
        r"\bconvenience\s+fee\b",
        r"\badditional\s+charges?\b",
        r"\bfees?\s+(?:may|will)\s+apply\b",
        r"\bcalculated\s+at\s+checkout\b",
        r"\bautomatically\s+added\b",
        r"\bpre[- ]selected\b",
        r"\bpre[- ]checked\b",
        r"\badded\s+to\s+(?:your\s+)?cart\b",
    ],

    "forced_action": [
        r"\bmust\s+(?:sign|register|create)\s+(?:up|an\s+account)\b",
        r"\bcreate\s+an\s+account\s+to\s+(?:continue|checkout|purchase)\b",
        r"\bsign\s+up\s+to\s+(?:continue|checkout|purchase)\b",
        r"\bregistration\s+required\b",
        r"\bsign[- ]in\s+required\b",
        r"\bmust\s+subscribe\b",
        r"\brequired\s+to\s+continue\b",
    ],
}


# ============================================================
# HEURISTIC EVIDENCE
# ============================================================

def _heuristic_evidence(
    threat: str,
    text: str,
    dom_signals: dict[str, Any],
):

    haystack = (text or "").lower()

    matches = []

    for pattern in PATTERNS.get(threat, []):

        m = re.search(
            pattern,
            haystack,
            flags=re.I
        )

        if m:
            matches.append(
                m.group(0)
            )

    # --------------------------------------------------------
    # Price evidence
    # --------------------------------------------------------

    if threat == "misdirection":

        old_price = dom_signals.get(
            "old_price"
        )

        current_price = dom_signals.get(
            "current_price"
        )

        if (
            old_price is not None
            and current_price is not None
            and old_price > current_price
        ):

            matches.append(
                f"price comparison: "
                f"{old_price:g} → {current_price:g}"
            )

    # --------------------------------------------------------
    # Fee evidence
    # --------------------------------------------------------

    if threat == "sneaking":

        if dom_signals.get(
            "checkout_fee_hint"
        ):

            matches.append(
                "fee-related text detected "
                "outside the main product price"
            )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Different evidence strengths.
    #
    # One clear signal should matter.
    # Multiple independent signals should matter MUCH more.
    # --------------------------------------------------------

    if not matches:
        confidence = 0.0

    elif len(matches) == 1:
        confidence = 0.50

    elif len(matches) == 2:
        confidence = 0.75

    elif len(matches) == 3:
        confidence = 0.90

    else:
        confidence = 1.0

    # A plain percentage discount is NOT automatically
    # considered highly suspicious.
    if (
        threat == "misdirection"
        and len(matches) == 1
        and re.search(
            r"\b\d{1,3}%\s*off\b",
            matches[0],
            flags=re.I
        )
    ):
        confidence = 0.25

    return (
        confidence,
        matches[:5]
    )


# ============================================================
# AI REASON
# ============================================================

def _ml_reason(
    threat: str,
    confidence: float
):

    pct = round(
        confidence * 100
    )

    label = THREAT_CONFIG[
        threat
    ]["label"].lower()

    return (
        f"AI model confidence: "
        f"{pct}% for {label}."
    )


# ============================================================
# RISK BADGE
# ============================================================

def _badge(total: int):

    if total <= 29:

        return {
            "label": "SAFE",
            "class": "safe",
            "color": "green",
        }

    if total <= 59:

        return {
            "label": "MEDIUM RISK",
            "class": "medium",
            "color": "yellow",
        }

    return {
        "label": "HIGH RISK",
        "class": "high",
        "color": "red",
    }


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_page(
    url: str,
    title: str,
    text: str,
    prices: list[dict[str, Any]],
    dom_signals: dict[str, Any],
    ml_predictions: dict[str, float],
):

    threats = []

    weighted_sum = 0.0
    detected_weight_sum = 0.0

    for threat, config in THREAT_CONFIG.items():

        # ----------------------------------------------------
        # AI evidence
        # ----------------------------------------------------

        ml_conf = float(
            ml_predictions.get(
                threat,
                0.0
            )
        )

        # ----------------------------------------------------
        # NLP / heuristic evidence
        # ----------------------------------------------------

        heuristic_conf, evidence = (
            _heuristic_evidence(
                threat,
                text,
                dom_signals
            )
        )

        # ----------------------------------------------------
        # EVIDENCE FUSION
        #
        # AI = 50%
        # Heuristics = 50%
        # ----------------------------------------------------

        fused = (
            0.50 * ml_conf
            +
            0.50 * heuristic_conf
        )

        # ----------------------------------------------------
        # DETECTION THRESHOLD
        #
        # Strong heuristic evidence is enough to surface
        # a threat even when the ML classifier is conservative.
        # ----------------------------------------------------

        should_show = (
            fused >= 0.30
            or heuristic_conf >= 0.50
        )

        if not should_show:
            continue

        # ----------------------------------------------------
        # INDIVIDUAL SCORE
        # ----------------------------------------------------

        score = round(
            fused * 100
        )

        # ----------------------------------------------------
        # OVERALL CONTRIBUTION
        # ----------------------------------------------------

        weighted_sum += (
            config["weight"]
            * fused
        )

        detected_weight_sum += (
            config["weight"]
        )

        reasons = []

        if evidence:

            reasons.append(
                "Detected page evidence: "
                +
                ", ".join(
                    f'"{e}"'
                    for e in evidence
                )
            )

        reasons.append(
            _ml_reason(
                threat,
                ml_conf
            )
        )

        threats.append({

            "id": threat,

            "label": config[
                "label"
            ],

            "score": score,

            "weight": config[
                "weight"
            ],

            "severity": config[
                "severity"
            ],

            "reasons": reasons,
        })

    # ========================================================
    # OVERALL SCORE
    # ========================================================
    #
    # F_i = 0.50(AI) + 0.50(heuristic)
    #
    # Overall =
    #
    # 100 × Σ(weight_i × F_i)
    #       -------------------
    #       Σ(weight_i)
    #
    # Only DETECTED threats are included.
    # ========================================================

    if detected_weight_sum > 0:
        base_score = (100.0*weighted_sum/detected_weight_sum)

        detected_count = len(threats)

        corroboration_bonus = (            15 * max(0, detected_count - 1)    )

        total = round(        base_score        +        corroboration_bonus    )

    else:

        total = 0

    total = max(
        0,
        min(
            100,
            total
        )
    )

    badge = _badge(
        total
    )

    threats.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return {

        "url": url,

        "title": title,

        "score": total,

        "risk": badge,

        "threats": threats,

        "formula": (
            "Individual threat = "
            "100 × (0.50 × AI confidence "
            "+ 0.50 × heuristic confidence). "
            "Overall = "
            "100 × Σ(weight × fused) / "
            "Σ(weight for detected threats)."
        ),

        "weights": {
            k: v["weight"]
            for k, v in THREAT_CONFIG.items()
        },
    }