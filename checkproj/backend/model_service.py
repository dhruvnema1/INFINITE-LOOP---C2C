from pathlib import Path
from typing import Any
import joblib


class PatternModel:
    def __init__(self, model_path: Path):
        self.model_path = model_path
        self.pipeline = None
        self.classes: list[str] = []
        self.loaded = False
        self._load()

    def _load(self):
        if not self.model_path.exists():
            return
        artifact = joblib.load(self.model_path)
        self.pipeline = artifact["pipeline"]
        self.classes = list(artifact["classes"])
        self.loaded = True

    def predict(self, text: str) -> dict[str, float]:
        probabilities = self.pipeline.predict_proba([text])[0]
        return {
            label: float(prob)
            for label, prob in zip(self.classes, probabilities)
        }
