import re
from typing import Any

# Weights are intentionally explicit so the final score is explainable.
THREAT_CONFIG = {
    "fake_urgency": {
        "label": "Fake urgency",
        "weight": 25,
        "severity": "high",
    },
    "misleading_discount": {
        "label": "Misleading discount",
        "weight": 25,
        "severity": "high",
    },
    "hidden_fees": {
        "label": "Hidden fees",
        "weight": 20,
        "severity": "high",
    },
    "scarcity": {
        "label": "Scarcity pressure",
        "weight": 15,
        "severity": "medium",
    },
    "forced_continuity": {
        "label": "Forced continuity",
        "weight": 15,
        "severity": "medium",
    },
}

# These are detection signals, not pre-fed page results. They are applied to
# text actually extracted from the page.
PATTERNS = {
    "fake_urgency": [
        r"\bonly\s+\d+\s*(?:minutes?|hours?)\b",
        r"\b(?:ends?|expires?)\s+(?:in|today|tonight)\b",
        r"\blast\s+chance\b",
        r"\bact\s+now\b",
        r"\bhurry\b",
        r"\bcountdown\b",
        r"\bdeal\s+ends\b",
    ],
    "misleading_discount": [
        r"\b\d{2,3}%\s*off\b",
        r"\bwas\s+\$?\s*\d+(?:\.\d{1,2})?\b",
        r"\bcompare\s+at\b",
        r"\blist\s+price\b",
        r"\bmarked\s+down\b",
        r"\brrp\b",
    ],
    "hidden_fees": [
        r"\bservice\s+fee\b",
        r"\bprocessing\s+fee\b",
        r"\bhandling\s+fee\b",
        r"\bplatform\s+fee\b",
        r"\bconvenience\s+fee\b",
        r"\badditional\s+charges?\b",
        r"\bfees?\s+(?:may|will)\s+apply\b",
        r"\bcalculated\s+at\s+checkout\b",
    ],
    "scarcity": [
        r"\bonly\s+\d+\s+(?:left|remaining|available)\b",
        r"\blow\s+stock\b",
        r"\blimited\s+(?:stock|quantity)\b",
        r"\bin\s+\d+\s+(?:carts?|baskets?)\b",
        r"\b\d+\s+people\s+(?:are\s+)?viewing\b",
    ],
    "forced_continuity": [
        r"\bfree\s+trial\b",
        r"\btrial\s+ends\b",
        r"\bautomatically\s+(?:renew|renews|renewed)\b",
        r"\bsubscription\b",
        r"\brecurring\b",
        r"\bcancel\s+anytime\b",
    ],
}


def _heuristic_evidence(threat: str, text: str, dom_signals: dict[str, Any]):
    haystack = text.lower()
    matches: list[str] = []

    for pattern in PATTERNS[threat]:
        m = re.search(pattern, haystack, flags=re.I)
        if m:
            matches.append(m.group(0))

    # DOM/price evidence is deliberately additive to the NLP model.
    if threat == "hidden_fees" and dom_signals.get("checkout_fee_hint"):
        matches.append("fee-related text detected outside the main price")

    if threat == "misleading_discount":
        old_price = dom_signals.get("old_price")
        current_price = dom_signals.get("current_price")
        if old_price and current_price and old_price > current_price:
            matches.append(f"price comparison: {old_price:g} → {current_price:g}")

    # Saturating heuristic confidence: first match is meaningful, repeated
    # independent signals raise confidence without exceeding 1.
    confidence = min(1.0, 0.25 * len(matches))
    if len(matches) >= 3:
        confidence = min(1.0, confidence + 0.20)

    return confidence, matches[:4]


def _ml_reason(threat: str, confidence: float) -> str:
    pct = round(confidence * 100)
    return f"AI language model confidence: {pct}% for {THREAT_CONFIG[threat]['label'].lower()}."


def _badge(total: int):
    if total <= 29:
        return {"label": "SAFE", "class": "safe", "color": "green"}
    if total <= 59:
        return {"label": "MEDIUM RISK", "class": "medium", "color": "yellow"}
    return {"label": "HIGH RISK", "class": "high", "color": "red"}


def analyze_page(
    url: str,
    title: str,
    text: str,
    prices: list[dict[str, Any]],
    dom_signals: dict[str, Any],
    ml_predictions: dict[str, float],
    comparison: dict[str, Any] | None = None,
):
    threats = []
    comparison = comparison or {"available": False}
    weighted_sum = 0.0
    weight_sum = float(sum(c["weight"] for c in THREAT_CONFIG.values()))

    for threat, config in THREAT_CONFIG.items():
        ml_conf = float(ml_predictions.get(threat, 0.0))
        heuristic_conf, evidence = _heuristic_evidence(threat, text, dom_signals)

        # NLP has the larger share; heuristics provide deterministic corroboration.
        fused = 0.65 * ml_conf + 0.35 * heuristic_conf

        # Cross-site evidence is deliberately limited to price-related threats.
        # It supports the model; it never overrides page evidence by itself.
        if comparison.get("available") and threat == "misleading_discount":
            cross_conf = float(comparison.get("confidence", 0.0))
            fused = min(1.0, fused + 0.20 * cross_conf)
            if cross_conf >= 0.50:
                evidence.append("Cross-site comparison: " + "; ".join(comparison.get("evidence", [])[:2]))
        raw_points = config["weight"] * fused
        weighted_sum += raw_points

        should_show = fused >= 0.35 or heuristic_conf >= 0.50
        if not should_show:
            continue

        score = round(fused * 100)
        reasons = []

        if evidence:
            reasons.append(
                "Detected page evidence: " + ", ".join(f'"{e}"' for e in evidence)
            )
        reasons.append(_ml_reason(threat, ml_conf))

        threats.append({
            "id": threat,
            "label": config["label"],
            "score": score,
            "weight": config["weight"],
            "severity": config["severity"],
            "reasons": reasons,
        })

    # Explicit normalization formula:
    # 100 * Σ(weight_i × fused_i) / Σ(weight_i)
    total = round(max(0.0, min(100.0, 100.0 * weighted_sum / weight_sum)))
    badge = _badge(total)

    threats.sort(key=lambda item: item["score"], reverse=True)

    return {
        "url": url,
        "title": title,
        "score": total,
        "risk": badge,
        "threats": threats,
        "comparison": comparison,
        "formula": (
            "100 × Σ(weight × (0.65×AI_confidence + 0.35×heuristic_confidence)) "
            "/ Σ(weight)"
        ),
        "weights": {k: v["weight"] for k, v in THREAT_CONFIG.items()},
    }
