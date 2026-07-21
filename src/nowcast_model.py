"""Robustness-oriented modelling of influenza search interest vs. surveillance.

Goes beyond raw correlation to answer two reviewer questions:

1. Does the Google Trends <-> INF_ALL association survive removal of the shared
   seasonal cycle (de-seasonalised / week-over-week correlations)?
2. As a nowcast, does Google Trends add predictive value *over a season-only
   baseline*, evaluated out-of-sample with a temporal split (not a random one)?

Run from the repository root:
    python src/nowcast_model.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit, train_test_split

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MERGED_WIDE = PROJECT_ROOT / "data" / "processed" / "merged_trends_influenza_wide.csv"

FLU_TERMS = ["grip", "virus gripa", "simptomi gripa"]
TARGET = "INF_ALL"
COVID_YEARS = {2020, 2021}


def load() -> pd.DataFrame:
    df = pd.read_csv(MERGED_WIDE).sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    # Seasonal harmonics (first harmonic): together sin+cos fit an arbitrary phase.
    w = 2 * np.pi * df["ISO_WEEK"] / 52.0
    df["week_sin"] = np.sin(w)
    df["week_cos"] = np.cos(w)
    df["flu_agg"] = df[FLU_TERMS].mean(axis=1)
    return df


def deseasonalise(series: pd.Series, week: pd.Series) -> pd.Series:
    """Return anomalies: value minus the week-of-year climatological mean."""
    clim = series.groupby(week).transform("mean")
    return series - clim


def rprint(name, x, y):
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(d) < 4 or d["x"].std() == 0 or d["y"].std() == 0:
        print(f"  {name:34} n/a")
        return
    r, p = pearsonr(d["x"], d["y"])
    print(f"  {name:34} r={r:+.3f}  p={p:.2e}  n={len(d)}")


def correlation_section(df: pd.DataFrame) -> None:
    print("=" * 68)
    print("1) CORRELATION: raw vs. de-seasonalised vs. week-over-week change")
    print("=" * 68)
    base = df.dropna(subset=[TARGET]).copy()
    print(f"Modelling sample: n={len(base)} weeks, "
          f"{int(base['ISO_YEAR'].min())}-{int(base['ISO_YEAR'].max())}, "
          f"ISO weeks {int(base['ISO_WEEK'].min())}-{int(base['ISO_WEEK'].max())}")

    for label, term in [("grip", "grip"), ("virus gripa", "virus gripa"),
                        ("simptomi gripa", "simptomi gripa"), ("flu-agg", "flu_agg")]:
        print(f"\n{label}:")
        rprint("raw", base[term], base[TARGET])
        rprint("de-seasonalised (anomalies)",
               deseasonalise(base[term], base["ISO_WEEK"]),
               deseasonalise(base[TARGET], base["ISO_WEEK"]))
        rprint("week-over-week change (diff)", base[term].diff(), base[TARGET].diff())

    # COVID sensitivity on the de-seasonalised flu aggregate
    print("\nCOVID sensitivity (de-seasonalised flu-agg, excluding 2020-2021):")
    sub = base[~base["ISO_YEAR"].isin(COVID_YEARS)]
    rprint("excl. 2020-2021",
           deseasonalise(sub["flu_agg"], sub["ISO_WEEK"]),
           deseasonalise(sub[TARGET], sub["ISO_WEEK"]))


def _fit_report(X_tr, y_tr, X_te, y_te):
    m = LinearRegression().fit(X_tr, y_tr)
    return (r2_score(y_te, m.predict(X_te)),
            np.sqrt(mean_squared_error(y_te, m.predict(X_te))))


def nowcast_section(df: pd.DataFrame) -> None:
    print("\n" + "=" * 68)
    print("2) NOWCAST: does Trends beat a season-only baseline, out-of-sample?")
    print("=" * 68)
    data = df.dropna(subset=[TARGET] + FLU_TERMS).sort_values("date").reset_index(drop=True)
    season = ["week_sin", "week_cos"]
    full = FLU_TERMS + season
    y = data[TARGET]

    # --- temporal holdout: first 70% train, last 30% test ---
    cut = int(len(data) * 0.70)
    tr, te = slice(0, cut), slice(cut, None)
    split_date = data["date"].iloc[cut].date()
    print(f"\nTemporal holdout: train n={cut} (up to {split_date}), test n={len(data)-cut}")
    r2_s, rmse_s = _fit_report(data[season][tr], y[tr], data[season][te], y[te])
    r2_f, rmse_f = _fit_report(data[full][tr], y[tr], data[full][te], y[te])
    print(f"  season only        R2={r2_s:+.3f}  RMSE={rmse_s:.2f}")
    print(f"  season + Trends    R2={r2_f:+.3f}  RMSE={rmse_f:.2f}")
    print(f"  -> Trends adds     dR2={r2_f - r2_s:+.3f}  dRMSE={rmse_f - rmse_s:+.2f}")

    # --- forward-chaining CV (honest out-of-sample) ---
    print("\nTimeSeriesSplit CV (5 folds, forward-chaining):")
    tscv = TimeSeriesSplit(n_splits=5)
    for name, cols in [("season only", season), ("season + Trends", full)]:
        r2s = []
        for tri, tei in tscv.split(data):
            r2s.append(_fit_report(data[cols].iloc[tri], y.iloc[tri],
                                   data[cols].iloc[tei], y.iloc[tei])[0])
        r2s = np.array(r2s)
        print(f"  {name:16} R2 = {r2s.mean():+.3f} ± {r2s.std():.3f}   folds={np.round(r2s,2)}")

    # --- the misleading random split, for contrast ---
    Xtr, Xte, ytr, yte = train_test_split(data[full], y, test_size=0.3, random_state=42)
    r2_rand, _ = _fit_report(Xtr, ytr, Xte, yte)
    print(f"\nNaive RANDOM split (invalid for time series), season+Trends: "
          f"R2={r2_rand:+.3f}  <- inflated, do not report")


def main() -> None:
    df = load()
    correlation_section(df)
    nowcast_section(df)


if __name__ == "__main__":
    main()
