# Dark Pattern Detector — Chrome MV3 + AI/NLP + Heuristics

A production-oriented starter for a Chrome Manifest V3 extension that scans the
currently visible e-commerce page and reports only patterns actually detected.

## Architecture

Chrome extension (MV3)
→ content.js extracts visible page text + selected price/DOM signals
→ background.js calls the local Python API
→ FastAPI backend runs:
   1. TF-IDF NLP + Logistic Regression model trained from an external CSV
   2. deterministic heuristics
   3. score fusion and normalization
→ popup renders threat score and evidence

The extension contains **no demo scan results and no hardcoded training dataset**.

## Threat classes

- fake_urgency
- misleading_discount
- hidden_fees
- scarcity
- forced_continuity
none (neutral/non-dark-pattern text)

You can remove/add classes by changing the external training data and the
THREAT_CONFIG in backend/scoring.py.

## Required dataset

Supply your own CSV to:

    training/data/dark_patterns.csv

Required columns:

    text,label

Example structure (not included with this project):

    text,label
    <real training example>,fake_urgency
    <real training example>,hidden_fees

Do not paste the examples into the extension. The training data stays outside
the extension and is used only to produce the model artifact.

## Train

Python 3.10+ recommended.

    cd backend
    pip install -r requirements.txt

Then from the project root:

    python training/train_model.py --data training/data/dark_patterns.csv --output backend/model.joblib

The script refuses to train if the CSV is missing or has invalid columns.

## Run API

    cd backend
    uvicorn app:app --host 127.0.0.1 --port 8000

The extension is intentionally restricted to the local API:

    http://127.0.0.1:8000

## Load extension

1. Open chrome://extensions
2. Enable Developer mode
3. Click Load unpacked
4. Select the `extension` folder.
5. Open an e-commerce page.
6. Click the extension icon and press Scan page.

## Scoring formula

For each threat:

    ML confidence      = model probability for that threat
    heuristic score    = normalized heuristic evidence in [0, 1]

    fused_confidence =
        0.65 * ML confidence +
        0.35 * heuristic score

    raw threat points =
        severity_weight * fused_confidence

The total is explicitly scaled to 0–100:

    total =
      100 * Σ(raw threat points) / Σ(severity weights)

The weights sum to 100, but the denominator is retained in the formula so the
score remains correctly normalized if weights are changed later.

Severity weights:
fake_urgency=25, misleading_discount=25, hidden_fees=20,
scarcity=15, forced_continuity=15.

Thresholds:
0–29 safe, 30–59 medium-risk, 60–100 high-risk.

A threat is displayed only when its fused confidence reaches 0.35 or there is
strong heuristic evidence. Evidence sentences are generated from the actual
page text/DOM signals sent by the scanner; there is no seeded demo output.

## Important limitation

A local Python server is required because Chrome extensions cannot directly
run a Python/scikit-learn model. The model artifact is generated from your
external dataset and loaded by the backend.
