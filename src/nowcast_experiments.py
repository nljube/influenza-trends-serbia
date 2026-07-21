"""Can Google Trends add predictive value once we model it properly?

Tests three ideas against honest, temporal (out-of-sample) validation:
  1. An autoregressive baseline (last known INF_ALL) — does Trends add *on top*?
  2. log1p target + per-fold standardisation (Trends is relative/renormalised).
  3. Direction task: predict whether influenza is rising or falling, not the count.

Run from the repository root:
    python src/nowcast_experiments.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import r2_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MERGED_WIDE = PROJECT_ROOT / "data" / "processed" / "merged_trends_influenza_wide.csv"
FLU = ["grip", "virus gripa", "simptomi gripa"]
CV = TimeSeriesSplit(n_splits=5)


def load() -> pd.DataFrame:
    df = pd.read_csv(MERGED_WIDE)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    w = 2 * np.pi * df["ISO_WEEK"] / 52.0
    df["week_sin"], df["week_cos"] = np.sin(w), np.cos(w)
    # date-based previous-week values (respects calendar gaps)
    inf = df.set_index("date")["INF_ALL"]
    df["ar1"] = df["date"].sub(pd.Timedelta(weeks=1)).map(inf.to_dict())
    for t in FLU:
        s = df.set_index("date")[t]
        df[f"{t}__d"] = df[t] - df["date"].sub(pd.Timedelta(weeks=1)).map(s.to_dict())
    df["flu_agg"] = df[FLU].mean(axis=1)
    return df


def cv_r2(df, cols, target="INF_ALL", model=None, log=False):
    d = df.dropna(subset=cols + [target]).reset_index(drop=True)
    X = d[cols].to_numpy(float)
    y = np.log1p(d[target].to_numpy(float)) if log else d[target].to_numpy(float)
    est = model or LinearRegression()
    scores = []
    for tri, tei in CV.split(X):
        est.fit(X[tri], y[tri])
        scores.append(r2_score(y[tei], est.predict(X[tei])))
    return np.array(scores), len(d)


def show(label, cols, **kw):
    s, n = cv_r2(DF, cols, **kw)
    print(f"  {label:34} R2 = {s.mean():+.3f} ± {s.std():.3f}   n={n}   folds={np.round(s,2)}")


DF = load()
season = ["week_sin", "week_cos"]

print("=" * 70)
print("A) REGRESSION on INF_ALL — does Trends add over season + autoregression?")
print("=" * 70)
print("(common sample = weeks with previous-week INF_ALL available)")
show("season only", season)
show("AR only (last week INF_ALL)", ["ar1"])
show("season + AR", season + ["ar1"])
show("season + AR + Trends", season + ["ar1"] + FLU)
show("season + Trends (no AR)", season + FLU)

print("\n" + "=" * 70)
print("B) Same, but log1p(INF_ALL) target + per-fold standardisation (Ridge)")
print("=" * 70)
ridge = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
show("season + AR", season + ["ar1"], target="INF_ALL", model=ridge, log=True)
ridge2 = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
show("season + AR + Trends", season + ["ar1"] + FLU, target="INF_ALL", model=ridge2, log=True)

print("\n" + "=" * 70)
print("C) DIRECTION task — predict whether influenza is RISING (ROC AUC)")
print("=" * 70)
d = DF.dropna(subset=["ar1"] + FLU + [f"{t}__d" for t in FLU]).copy()
d["delta"] = d["INF_ALL"] - d["ar1"]
d = d[d["delta"] != 0]
y = (d["delta"] > 0).astype(int).to_numpy()
print(f"  n={len(d)}  rising weeks={y.mean():.0%}")

def auc(cols):
    X = d[cols].to_numpy(float)
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    aucs = []
    for tri, tei in CV.split(X):
        if len(np.unique(y[tei])) < 2:
            continue
        clf.fit(X[tri], y[tri])
        aucs.append(roc_auc_score(y[tei], clf.predict_proba(X[tei])[:, 1]))
    return np.array(aucs)

for label, cols in [
    ("season only", season),
    ("Trends level", FLU),
    ("Trends weekly change", [f"{t}__d" for t in FLU]),
    ("season + Trends (level+change)", season + FLU + [f"{t}__d" for t in FLU]),
]:
    a = auc(cols)
    print(f"  {label:34} AUC = {a.mean():.3f} ± {a.std():.3f}   folds={np.round(a,2)}")
