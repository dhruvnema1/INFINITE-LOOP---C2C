import re
from typing import Dict, List, Any

# Dark Pattern Guardian - Data / Regex MVP
# Deterministic, explainable rules for webpage text.

RULES = [
    ("Fake Scarcity", r"\bonly\s+\d+\s+(?:left|remaining|items?|units?)\b", 20,
     "Limited-stock wording may pressure the user to purchase quickly."),
    ("Fake Scarcity", r"\b(?:limited|low)\s+(?:stock|inventory|availability)\b", 15,
     "The page uses limited-availability language."),
    ("Fake Urgency", r"\b(?:hurry|act\s+now|buy\s+now|order\s+now)\b", 15,
     "Urgency language may encourage a rushed decision."),
    ("Fake Urgency", r"\b(?:limited\s+time|ends?\s+soon|ending\s+soon|offer\s+ends?)\b", 20,
     "The offer is presented as time-limited."),
    ("Social Proof", r"\b\d+\s+(?:people|users|shoppers|customers)\s+(?:are\s+)?viewing\b", 15,
     "A viewer-count message may influence the user through perceived popularity."),
    ("Social Proof", r"\b\d+\s+(?:people|customers|users)\s+(?:bought|purchased|ordered)\b", 15,
     "A purchase-count message may use popularity to influence the decision."),
    ("Confirmshaming", r"\bno[,.\s]+(?:thanks|thank\s+you)[,.\s]+(?:i\s+)?(?:don't|do\s+not)\s+(?:want|need)\b", 15,
     "The refusal option may shame the user for declining an offer."),
    ("Hidden Fees", r"\b(?:handling|service|processing|platform|convenience)\s+fee\b", 20,
     "An additional fee is present in the page text."),
    ("Hidden Fees", r"\b(?:additional|extra|other)\s+(?:charges?|fees?|costs?)\b", 20,
     "The page mentions additional charges beyond the displayed price."),
]

def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def risk_level(score: int) -> str:
    if score >= 60:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"

def get_evidence(text: str, match: re.Match, window: int = 60) -> str:
    start = max(0, match.start() - window)
    end = min(len(text), match.end() + window)
    return text[start:end].strip()

def scan_text(text: str) -> Dict[str, Any]:
    """Scan webpage text and return explainable dark-pattern findings."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    text = normalize_text(text)
    findings: List[Dict[str, Any]] = []

    for category, pattern, points, reason in RULES:
        regex = re.compile(pattern, re.IGNORECASE)

        # Limit repeated matches so a page cannot inflate the score
        # simply by repeating the same sentence many times.
        for match in list(regex.finditer(text))[:3]:
            findings.append({
                "category": category,
                "evidence": get_evidence(text, match),
                "points": points,
                "reason": reason,
            })

    score = min(sum(item["points"] for item in findings), 100)

    return {
        "risk_score": score,
        "risk_level": risk_level(score),
        "categories_detected": sorted({
            item["category"] for item in findings
        }),
        "findings": findings,
    }


if __name__ == "__main__":
    import json

    sample = """
    Flash Sale! Hurry! Offer ends soon.
    Only 2 left in stock!
    34 people are viewing this item.
    A handling fee will be added at checkout.
    """

    print(json.dumps(scan_text(sample), indent=2))