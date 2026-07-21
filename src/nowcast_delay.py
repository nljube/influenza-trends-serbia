"""Does Google Trends add value when surveillance is reported with a delay?

If surveillance is k weeks late, the best available "carry-forward" value at week t
is INF_ALL[t-k]. Google Trends[t] is available in real time. We test, for k = 1,2,3:
  - full model:  season + AR_k        vs   season + AR_k + Trends[t]
  - gap model:   predict INF_ALL[t] - AR_k (the change since the last known value)
                 from season           vs   season + Trends[t]
All evaluated out-of-sample with TimeSeriesSplit.

Run from the repository root:
    python src/nowcast_delay.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
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
    inf = df.set_index("date")["INF_ALL"].to_dict()
    for k in (1, 2, 3):
        df[f"ar{k}"] = df["date"].sub(pd.Timedelta(weeks=k)).map(inf)
    return df


def cv_r2(d, cols, y):
    X = d[cols].to_numpy(float)
    s = []
    for tri, tei in CV.split(X):
        est = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
        est.fit(X[tri], y[tri])
        s.append(r2_score(y[tei], est.predict(X[tei])))
    return np.array(s)


DF = load()
season = ["week_sin", "week_cos"]

print("=" * 72)
print("FULL MODEL: predict INF_ALL[t]  (baseline = last available value, k weeks old)")
print("=" * 72)
for k in (1, 2, 3):
    ark = f"ar{k}"
    d = DF.dropna(subset=[ark, "INF_ALL"] + FLU).reset_index(drop=True)
    y = d["INF_ALL"].to_numpy(float)
    base = cv_r2(d, season + [ark], y)
    full = cv_r2(d, season + [ark] + FLU, y)
    print(f"\ndelay k={k} weeks   (n={len(d)})")
    print(f"  season + AR{k}            R2 = {base.mean():+.3f} ± {base.std():.3f}")
    print(f"  season + AR{k} + Trends   R2 = {full.mean():+.3f} ± {full.std():.3f}"
          f"   -> Trends dR2 = {full.mean()-base.mean():+.3f}")

print("\n" + "=" * 72)
print("GAP MODEL: predict INF_ALL[t] - AR_k  (the change since the last known value)")
print("=" * 72)
for k in (1, 2, 3):
    ark = f"ar{k}"
    d = DF.dropna(subset=[ark, "INF_ALL"] + FLU).reset_index(drop=True)
    y = (d["INF_ALL"] - d[ark]).to_numpy(float)
    base = cv_r2(d, season, y)
    full = cv_r2(d, season + FLU, y)
    print(f"\ndelay k={k} weeks   (n={len(d)},  gap std={y.std():.1f})")
    print(f"  season only              R2 = {base.mean():+.3f} ± {base.std():.3f}")
    print(f"  season + Trends          R2 = {full.mean():+.3f} ± {full.std():.3f}"
          f"   -> Trends dR2 = {full.mean()-base.mean():+.3f}")
