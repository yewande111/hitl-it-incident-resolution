"""Use the ticket classifier on any ticket text, with the review rules from the dissertation.

The main model is the fine-tuned DistilBERT model saved by step 4 (folder results/final_model, downloaded from
Kaggle). Running it on a laptop needs PyTorch and transformers:  python3 -m pip install torch transformers
If that folder is not there, the tool falls back to the baseline (TF-IDF + Logistic Regression), which has to be
trained once with the train command.

Usage:
    python3 ticket_model.py predict "cannot log in to my account please reset password"
    python3 ticket_model.py train        (baseline only, about a minute)
"""
import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "dataset" / "all_tickets_processed_improved_v3.csv"
RESULTS = HERE / "results"
DISTILBERT_DIR = RESULTS / "final_model"
BASELINE_FILE = HERE / "ticket_model.joblib"

# Review rules. The values chosen in step 2 (or step 1 for the baseline) are read from the results file if present.
SENSITIVE = ["Administrative rights"]
DEFAULT_RULES = {"general_threshold": 0.70, "sensitive_threshold": 0.95, "watch_threshold": 0.01}


def load_rules(results_file):
    if not results_file.exists():
        return DEFAULT_RULES
    sec = json.load(open(results_file))["security"]
    return {"general_threshold": sec["general_threshold"], "sensitive_threshold": sec["chosen"]["sensitive_threshold"],
            "watch_threshold": sec["chosen"]["watch_threshold"]}


def train():
    import joblib
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    df = pd.read_csv(DATA).dropna()
    # Same 80/20 split as the dissertation. Only the 80% training part is used here.
    X_train, _, y_train, _ = train_test_split(
        df["Document"], df["Topic_group"], test_size=0.2, random_state=42, stratify=df["Topic_group"]
    )
    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
        ("classifier", LogisticRegression(max_iter=2000, C=10)),
    ])
    print(f"Training the baseline on {len(X_train)} tickets (this takes about a minute)...")
    model.fit(X_train, y_train)
    joblib.dump(model, BASELINE_FILE)
    print("Saved baseline model to", BASELINE_FILE)


def distilbert_proba(text):
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    info = json.load(open(DISTILBERT_DIR / "temperature.json"))
    tokenizer = AutoTokenizer.from_pretrained(DISTILBERT_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(DISTILBERT_DIR).eval()
    with torch.no_grad():
        logits = model(**tokenizer([text], truncation=True, max_length=info["max_len"], return_tensors="pt")).logits
    proba = torch.softmax(logits[0] / info["temperature"], dim=0).numpy()
    return np.array(info["classes"]), proba


def predict(text):
    if DISTILBERT_DIR.exists():
        name, rules = "DistilBERT", load_rules(RESULTS / "transformer_cv_results.json")
        classes, proba = distilbert_proba(text)
    elif BASELINE_FILE.exists():
        import joblib
        name, rules = "baseline (TF-IDF + Logistic Regression)", load_rules(RESULTS / "cv_results.json")
        model = joblib.load(BASELINE_FILE)
        classes, proba = model.classes_, model.predict_proba([text])[0]
    else:
        sys.exit("No saved model found. Download results/final_model from Kaggle (step 4), "
                 "or train the baseline with:  python3 ticket_model.py train")

    order = proba.argsort()[::-1]
    predicted, confidence = classes[order[0]], proba[order[0]]
    sensitive_proba = max(proba[list(classes).index(c)] for c in SENSITIVE)

    print(f"Model: {name}")
    print(f"Ticket: {text}")
    print(f"Predicted category: {predicted}")
    print(f"Confidence: {confidence * 100:.0f}%")
    print("Top 3 categories:")
    for i in order[:3]:
        print(f"  {classes[i]}: {proba[i] * 100:.0f}%")

    g, s, w = rules["general_threshold"], rules["sensitive_threshold"], rules["watch_threshold"]
    if confidence < g:
        reason = f"confidence is below {g * 100:.0f}%"
    elif predicted in SENSITIVE and confidence < s:
        reason = f"it is a security-sensitive category ({predicted}) and confidence is below {s * 100:.0f}%"
    elif predicted not in SENSITIVE and w is not None and sensitive_proba >= w:
        reason = (f"it might be a security-sensitive ticket: {', '.join(SENSITIVE)} has {sensitive_proba * 100:.1f}%, "
                  f"which is {w * 100:.0f}% or more")
    else:
        reason = None
    if reason:
        print(f"Decision: send to the human reviewer, because {reason}")
    else:
        print("Decision: accept the AI answer")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "train":
        train()
    elif len(sys.argv) >= 3 and sys.argv[1] == "predict":
        predict(" ".join(sys.argv[2:]))
    else:
        print(__doc__)
