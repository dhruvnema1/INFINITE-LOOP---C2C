from pathlib import Path
import re
import joblib


# Dataset category -> scoring system ID
CATEGORY_MAP = {
    "Urgency": "urgency",
    "Scarcity": "scarcity",
    "Social Proof": "social_proof",
    "Misdirection": "misdirection",
    "Obstruction": "obstruction",
    "Sneaking": "sneaking",
    "Forced Action": "forced_action",
}


class PatternModel:

    def __init__(self, model_path: Path):
        self.model_path = model_path
        self.pipeline = None
        self.classes = []
        self.loaded = False

        self._load()

    def _load(self):

        if not self.model_path.exists():
            return

        artifact = joblib.load(
            self.model_path
        )

        self.pipeline = artifact["pipeline"]
        self.classes = list(
            artifact["classes"]
        )

        self.loaded = True

    def predict(self, text: str):

        # Normalize page text
        clean = re.sub(
            r"\s+",
            " ",
            text or ""
        ).strip()

        if not clean:
            return {
                threat_id: 0.0
                for threat_id in CATEGORY_MAP.values()
            }

        # Split the page into smaller pieces.
        chunks = [
            c.strip()
            for c in re.split(
                r"(?<=[.!?])\s+|[|•]",
                clean
            )
            if c.strip()
        ]

        # Add overlapping windows for fragmented DOM text.
        words = clean.split()

        for i in range(
            0,
            len(words),
            35
        ):
            window = " ".join(
                words[i:i + 55]
            ).strip()

            if window:
                chunks.append(window)

        chunks = chunks[:500]

        # AI probabilities
        probabilities = (
            self.pipeline.predict_proba(
                chunks
            )
        )

        result = {
            threat_id: 0.0
            for threat_id in CATEGORY_MAP.values()
        }

        # Convert:
        #
        # "Urgency" -> "urgency"
        # "Scarcity" -> "scarcity"
        # etc.
        #
        # Not Dark Pattern is intentionally ignored.
        for index, category in enumerate(
            self.classes
        ):

            threat_id = CATEGORY_MAP.get(
                str(category)
            )

            if not threat_id:
                continue

            values = sorted(
                (
                    float(row[index])
                    for row in probabilities
                ),
                reverse=True
            )

            # Strongest five chunks
            top = values[:5]

            if top:
                result[threat_id] = (
                    sum(top) / len(top)
                )

        return result