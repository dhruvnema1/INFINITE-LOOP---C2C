import argparse
from pathlib import Path
import csv
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


ALLOWED_CATEGORIES = {
    "Not Dark Pattern",
    "Forced Action",
    "Misdirection",
    "Obstruction",
    "Scarcity",
    "Sneaking",
    "Social Proof",
    "Urgency",
}


def load_dataset(path: Path):

    if not path.exists():
        raise SystemExit(f"Dataset not found: {path}")

    texts = []
    labels = []

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        # IMPORTANT: TSV = tab separated
        reader = csv.DictReader(
            f,
            delimiter="\t"
        )

        print("Columns found:")
        print(reader.fieldnames)

        required = {
            "text",
            "Pattern Category"
        }

        if not required.issubset(
            set(reader.fieldnames or [])
        ):
            raise SystemExit(
                "Dataset must contain "
                "'text' and 'Pattern Category' columns."
            )

        for row in reader:

            text = (
                row.get("text") or ""
            ).strip()

            category = (
                row.get("Pattern Category") or ""
            ).strip()

            if not text or not category:
                continue

            if category not in ALLOWED_CATEGORIES:
                print(
                    f"Skipping unknown category: {category}"
                )
                continue

            texts.append(text)
            labels.append(category)

    if len(texts) < 20:
        raise SystemExit(
            f"Dataset is too small: {len(texts)} rows."
        )

    if len(set(labels)) < 2:
        raise SystemExit(
            "Dataset needs at least two categories."
        )

    return texts, labels


def train(
    data_path: Path,
    output_path: Path
):

    texts, labels = load_dataset(
        data_path
    )

    print()
    print(
        f"Training rows: {len(texts)}"
    )

    print()
    print("Category counts:")

    counts = {}

    for label in labels:
        counts[label] = (
            counts.get(label, 0) + 1
        )

    for label, count in sorted(
        counts.items()
    ):
        print(
            f"  {label}: {count}"
        )

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

    pipeline.fit(
        texts,
        labels
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    joblib.dump(
        {
            "pipeline": pipeline,
            "classes": list(
                pipeline.classes_
            ),
            "training_rows": len(texts),
        },
        output_path,
    )

    print()
    print("==============================")
    print("MODEL TRAINED SUCCESSFULLY")
    print("==============================")
    print(
        f"Rows: {len(texts)}"
    )
    print(
        "Classes:"
    )

    for c in pipeline.classes_:
        print(
            f"  - {c}"
        )

    print()
    print(
        f"Saved: {output_path}"
    )


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--data",
        required=True,
        type=Path
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path
    )

    args = parser.parse_args()

    train(
        args.data,
        args.output
    )