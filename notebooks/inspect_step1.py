# inspect_step1.py
# READ-ONLY. Prints facts about the project database, saved models and the
# vital-signs dataset. It never writes to the database or the dataset.
#
# Run from the NeuroTriage folder:
#   python notebooks\inspect_step1.py
# or with an explicit dataset path:
#   python notebooks\inspect_step1.py "dataset\Synthetic_patient-HealthCare-Monitoring_dataset.csv"

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "backend" / "database" / "neurotriage.db"
INFO = ROOT / "backend" / "ml" / "model_info.json"


def heading(text):
    print("\n" + "=" * 70 + f"\n{text}\n" + "=" * 70)


def part_a_project():
    heading("A. PROJECT FILES (size in KB)")
    for folder in ["backend/routes", "backend/services", "backend/ml", "frontend/templates"]:
        for f in sorted((ROOT / folder).glob("*")):
            if f.is_file() and f.suffix in (".py", ".html", ".json", ".joblib", ".npz"):
                print(f"  {folder}/{f.name:<28} {f.stat().st_size // 1024:>6} KB")

    heading("B. DATABASE (opened read-only)")
    if not DB.exists():
        print("  Database file not found.")
        return
    conn = sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    tables = [r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    for t in tables:
        cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({t})")]
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t} ({n} rows): {', '.join(cols)}")
    if "priority_mapping" in tables:
        print("\n  priority_mapping:")
        for r in conn.execute("SELECT class_name, priority_label FROM priority_mapping"):
            print(f"    {r['class_name']:<12} -> {r['priority_label']}")
    if "predictions" in tables:
        print("\n  predictions by priority_label (counts only):")
        for r in conn.execute("SELECT priority_label, COUNT(*) c FROM predictions GROUP BY 1"):
            print(f"    {r['priority_label']}: {r['c']}")
    conn.close()

    heading("C. SAVED EEG MODEL INFO")
    if INFO.exists():
        info = json.loads(INFO.read_text(encoding="utf-8"))
        for k in ["model", "classes", "n_features", "n_training_trials",
                  "trained_at_utc", "scikit_learn_version", "dataset", "cross_validation"]:
            print(f"  {k}: {info.get(k)}")
    else:
        print("  model_info.json not found.")


# ---------------------------------------------------------------- dataset
RANGES = [  # (name keywords, low, high) - DATA-ENTRY plausibility only, NOT clinical thresholds
    (("heart", "pulse", "hr"), 20, 300),
    (("spo2", "oxygen"), 50, 100),
    (("systolic", "sbp"), 40, 300),
    (("diastolic", "dbp"), 20, 200),
]


def find_csv():
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    for f in (ROOT / "dataset").glob("*.csv"):
        n = f.name.lower()
        if "health" in n and "monitor" in n:
            return f
    return None


def part_d_dataset():
    path = find_csv()
    heading("D. VITAL-SIGNS DATASET")
    if path is None or not path.exists():
        print("  Dataset not found. Put it in the dataset folder or pass its path.")
        return
    df = pd.read_csv(path, low_memory=False)
    print(f"  File: {path.name}\n  Rows: {len(df)}   Columns: {df.shape[1]}")

    print("\n  COLUMNS (name | dtype | missing | unique)")
    for c in df.columns:
        print(f"   {str(c)[:38]:<38} | {str(df[c].dtype):<8} | {int(df[c].isna().sum()):>6} | {df[c].nunique(dropna=True):>7}")

    print("\n  DUPLICATES")
    print("   fully duplicated rows:", int(df.duplicated().sum()))

    id_cols = [c for c in df.columns
               if any(h in str(c).lower() for h in ("id", "patient", "name", "subject"))
               or (df[c].dtype == object and df[c].nunique() > 0.5 * len(df))]
    print("\n  POSSIBLE IDENTIFIER COLUMNS:", id_cols or "none found")
    for c in id_cols:
        sizes = df.groupby(c).size()
        print(f"   {c}: {sizes.shape[0]} distinct values, records per value min/median/max = "
              f"{sizes.min()}/{int(sizes.median())}/{sizes.max()}")

    num = df.select_dtypes(include=["number", "bool"]).copy()
    for c in num.columns:
        num[c] = num[c].astype(float)
    print("\n  NUMERIC SUMMARY (min | mean | max)")
    for c in num.columns:
        print(f"   {str(c)[:38]:<38} {num[c].min():>10.2f} {num[c].mean():>10.2f} {num[c].max():>10.2f}")

    print("\n  PLAUSIBILITY SCREEN (typing-error ranges, not clinical thresholds)")
    for c in num.columns:
        name = str(c).lower()
        for keys, lo, hi in RANGES:
            if any(k in name for k in keys):
                bad = int(((num[c] < lo) | (num[c] > hi)).sum())
                print(f"   {c}: {bad} values outside {lo}-{hi}")
        if "temp" in name:
            lo, hi = (77, 113) if num[c].median() > 60 else (25, 45)
            bad = int(((num[c] < lo) | (num[c] > hi)).sum())
            print(f"   {c}: {bad} values outside {lo}-{hi} (unit guessed from the median)")

    low_card = [c for c in df.columns if df[c].nunique(dropna=True) <= 15 and c not in id_cols]
    print("\n  LOW-CARDINALITY COLUMNS (possible labels / alerts)")
    for c in low_card:
        print(f"   {c}:")
        for v, n in df[c].value_counts(dropna=False).items():
            print(f"      {str(v)[:30]:<30} {n:>8} ({100 * n / len(df):.1f}%)")

    # Is a label determined by other columns? (hint of rule-generated labels / leakage)
    hints = ("disease", "predict", "label", "target", "class", "diagnos")
    targets = [c for c in low_card if any(h in str(c).lower() for h in hints)]
    print("\n  LEAKAGE CHECK: how well does ONE column alone determine each candidate label?")
    for t in targets:
        print(f"   Candidate label: {t}")
        for x in low_card:
            if x == t:
                continue
            purity = df.groupby(x)[t].agg(lambda s: s.value_counts().iloc[0]).sum() / len(df)
            if purity >= 0.9:
                print(f"      {x}: majority-label purity {purity:.3f}  <-- strongly related")

        # Quick tree on numeric columns only: do simple thresholds recreate the label?
        from sklearn.model_selection import train_test_split
        from sklearn.tree import DecisionTreeClassifier
        feats = [c for c in num.columns if c not in id_cols and c != t]
        sub = pd.concat([num[feats], df[t]], axis=1).dropna()
        if len(feats) and sub[t].nunique() > 1:
            Xtr, Xte, ytr, yte = train_test_split(sub[feats], sub[t], test_size=0.2,
                                                  random_state=0, stratify=sub[t])
            for depth in (3, None):
                acc = DecisionTreeClassifier(max_depth=depth, random_state=0).fit(Xtr, ytr).score(Xte, yte)
                print(f"      Decision tree (max_depth={depth}) on numeric columns: "
                      f"random-split test accuracy {acc:.3f}")
    print("\n  (This section only inspects. It does not train or save anything.)")


part_a_project()
part_d_dataset()
print("\nEnd of report. Nothing was changed.")