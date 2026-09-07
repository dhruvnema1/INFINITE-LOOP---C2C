import argparse
from pathlib import Path
import csv
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


ALLOWED_LABELS = {
    "fake_urgency",
    "misleading_discount",
    "hidden_fees",
    "scarcity",
    "forced_continuity",
    "none",
}


def load_dataset(path: Path):
    if not path.exists():
        raise SystemExit(
            f"Dataset not found: {path}\n"
            "Provide your own external CSV with columns: text,label"
        )

    texts, labels = [], []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"text", "label"}
        if not required.issubset(reader.fieldnames or set()):
            raise SystemExit("Dataset must contain CSV columns: text,label")

        for row in reader:
            text = (row.get("text") or "").strip()
            label = (row.get("label") or "").strip()

            if not text or not label:
                continue
            if label not in ALLOWED_LABELS:
                raise SystemExit(
                    f"Unsupported label '{label}'. Allowed labels: "
                    f"{', '.join(sorted(ALLOWED_LABELS))}"
                )

            texts.append(text)
            labels.append(label)

    if len(texts) < 20:
        raise SystemExit(
            "Dataset is too small. Provide at least 20 labeled rows; "
            "a real project should use substantially more."
        )

    if len(set(labels)) < 2:
        raise SystemExit("Dataset needs at least two different labels.")

    return texts, labels


def train(data_path: Path, output_path: Path):
    texts, labels = load_dataset(data_path)

    pipeline = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                strip_accents="unicode",
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.98,
                sublinear_tf=True,
            ),
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                random_state=42,
            ),
        ),
    ])

    pipeline.fit(texts, labels)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "pipeline": pipeline,
            "classes": list(pipeline.classes_),
            "training_rows": len(texts),
        },
        output_path,
    )

    print(f"Trained AI model with {len(texts)} rows.")
    print(f"Classes: {', '.join(pipeline.classes_)}")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    train(args.data, args.output)
