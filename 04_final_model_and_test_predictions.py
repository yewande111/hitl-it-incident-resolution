"""Step 4. Final DistilBERT model and its predictions for the 20 percent test portion.
Run this on Kaggle (free GPU T4) after step 2 - see README.txt.

The model is fine-tuned once on the 80 percent training portion (90 percent of it for training, 10 percent kept aside
to fit the temperature, exactly as in each fold of step 2), with the same settings as step 2. It then predicts every
ticket in the test portion. This is the only script that touches the test portion, and it only records the model's
predictions; the conditions are compared in step 5.

Outputs (in /kaggle/working on Kaggle, otherwise code/results):
  test_predictions.csv  for each test ticket: its row in the dataset, correct category, predicted category,
                        confidence and the probability of every category
  final_model/          the fine-tuned model, tokenizer and temperature (used by ticket_model.py)

Set QUICK_TEST=1 to run a tiny version on a laptop CPU just to check the code works.
"""
import os
import glob
import json
import time
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from scipy.special import softmax, log_softmax
from sklearn.model_selection import train_test_split
from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup

QUICK_TEST = os.environ.get("QUICK_TEST") == "1"

# Same settings as 02_transformer_cross_validation.py
MODEL_NAME = "distilbert-base-uncased"
MAX_LEN = 64 if QUICK_TEST else 256
BATCH_SIZE = 32
EPOCHS = 1 if QUICK_TEST else 3
LEARNING_RATE = 5e-5
WEIGHT_DECAY = 0.01
WARMUP_SHARE = 0.1
CALIBRATION_SHARE = 0.1
SEED = 42

DATA_NAME = "all_tickets_processed_improved_v3.csv"
HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()


def find_data():
    for pattern in [f"/kaggle/input/**/{DATA_NAME}", f"/content/**/{DATA_NAME}",
                    str(HERE.parent / "dataset" / DATA_NAME), str(HERE / DATA_NAME)]:
        hits = glob.glob(pattern, recursive=True)
        if hits:
            return hits[0]
    raise FileNotFoundError(f"Cannot find {DATA_NAME}. On Kaggle, add the dataset 'IT Service Ticket Classification "
                            "Dataset' with '+ Add Input'. On Colab, upload the csv file first.")


OUT = Path("/kaggle/working") if Path("/kaggle/working").exists() else HERE / "results"
OUT.mkdir(exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
USE_AMP = DEVICE.type == "cuda"
if DEVICE.type != "cuda" and not QUICK_TEST and os.environ.get("ALLOW_CPU") != "1":
    raise SystemExit("No GPU found. On Kaggle open Settings > Accelerator and choose GPU T4 x2 (or P100), then run again.")
print("device:", DEVICE, "| quick test" if QUICK_TEST else "")


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


# Same 80/20 split as every other step. The row numbers of the test tickets are kept so they can be traced back.
df = pd.read_csv(find_data()).dropna()
X_train, X_test, y_train, y_test = train_test_split(
    df["Document"], df["Topic_group"], test_size=0.2, random_state=42, stratify=df["Topic_group"]
)
if QUICK_TEST:
    X_train, _, y_train, _ = train_test_split(X_train, y_train, train_size=1000, random_state=SEED, stratify=y_train)
    X_test, _, y_test, _ = train_test_split(X_test, y_test, train_size=300, random_state=SEED, stratify=y_test)
print("training tickets:", len(X_train), "| test tickets:", len(X_test))

CLASSES = np.array(sorted(y_train.unique()))
y = np.searchsorted(CLASSES, y_train.values)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
ENC = tokenizer(X_train.tolist(), truncation=True, max_length=MAX_LEN)["input_ids"]
ENC_TEST = tokenizer(X_test.tolist(), truncation=True, max_length=MAX_LEN)["input_ids"]


def collate(batch):
    n = max(len(ids) for ids, _ in batch)
    input_ids = torch.full((len(batch), n), tokenizer.pad_token_id, dtype=torch.long)
    mask = torch.zeros((len(batch), n), dtype=torch.long)
    for i, (ids, _) in enumerate(batch):
        input_ids[i, :len(ids)] = torch.tensor(ids)
        mask[i, :len(ids)] = 1
    labels = torch.tensor([lab for _, lab in batch], dtype=torch.long)
    return {"input_ids": input_ids, "attention_mask": mask, "labels": labels}


def make_loader(encoded, labels, shuffle, batch_size=BATCH_SIZE, seed=SEED):
    g = torch.Generator()
    g.manual_seed(seed)
    return DataLoader(list(zip(encoded, labels)), batch_size=batch_size, shuffle=shuffle,
                      collate_fn=collate, generator=g)


def train_model(idx, seed):
    set_seed(seed)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=len(CLASSES),
        id2label={i: c for i, c in enumerate(CLASSES)}, label2id={c: i for i, c in enumerate(CLASSES)}).to(DEVICE)
    loader = make_loader([ENC[i] for i in idx], y[idx], shuffle=True, seed=seed)
    optimiser = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    total = len(loader) * EPOCHS
    scheduler = get_linear_schedule_with_warmup(optimiser, int(WARMUP_SHARE * total), total)
    scaler = (torch.amp.GradScaler("cuda", enabled=USE_AMP) if hasattr(torch, "amp") and hasattr(torch.amp, "GradScaler")
              else torch.cuda.amp.GradScaler(enabled=USE_AMP))
    model.train()
    for epoch in range(EPOCHS):
        start, running = time.time(), 0.0
        for step, batch in enumerate(loader, 1):
            batch = {k: v.to(DEVICE) for k, v in batch.items()}
            with torch.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=USE_AMP):
                loss = model(**batch).loss
            optimiser.zero_grad()
            scaler.scale(loss).backward()
            scaler.unscale_(optimiser)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimiser)
            scaler.update()
            scheduler.step()
            running += loss.item()
            if step % 200 == 0:
                print(f"  epoch {epoch + 1} step {step}/{len(loader)} loss {running / step:.4f}")
        print(f"  epoch {epoch + 1} done, loss {running / len(loader):.4f}, {(time.time() - start) / 60:.1f} min")
    model.eval()
    return model


@torch.no_grad()
def logits_for(model, encoded):
    out = []
    for batch in make_loader(encoded, np.zeros(len(encoded), dtype=int), shuffle=False, batch_size=128):
        batch = {k: v.to(DEVICE) for k, v in batch.items() if k != "labels"}
        with torch.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=USE_AMP):
            out.append(model(**batch).logits.float().cpu().numpy())
    return np.concatenate(out)


def fit_temperature(logits, labels):
    grid = np.round(np.arange(0.50, 5.001, 0.01), 2)
    nll = [-log_softmax(logits / t, axis=1)[np.arange(len(labels)), labels].mean() for t in grid]
    return float(grid[int(np.argmin(nll))])


start = time.time()
all_idx = np.arange(len(ENC))
fit_idx, cal_idx = train_test_split(all_idx, test_size=CALIBRATION_SHARE, random_state=SEED, stratify=y)
model = train_model(fit_idx, SEED)
temperature = fit_temperature(logits_for(model, [ENC[i] for i in cal_idx]), y[cal_idx])
print("temperature:", temperature)

proba = softmax(logits_for(model, ENC_TEST) / temperature, axis=1)
pred = proba.argmax(axis=1)
out = pd.DataFrame(proba, columns=[f"p_{c}" for c in CLASSES])
out.insert(0, "confidence", proba.max(axis=1))
out.insert(0, "predicted_category", CLASSES[pred])
out.insert(0, "true_category", y_test.values)
out.insert(0, "dataset_row", X_test.index.values)
out.to_csv(OUT / "test_predictions.csv", index=False)

model_dir = OUT / "final_model"
model.save_pretrained(model_dir)
tokenizer.save_pretrained(model_dir)
json.dump({"temperature": temperature, "max_len": MAX_LEN, "classes": CLASSES.tolist(), "quick_test": QUICK_TEST},
          open(model_dir / "temperature.json", "w"), indent=2)
print(f"saved {OUT / 'test_predictions.csv'} and {model_dir} ({(time.time() - start) / 60:.0f} minutes)")
