"""Summarize Google Trends keyword relationships with influenza indicators.

Inputs:
    Processed Google Trends CSV and influenza surveillance Excel data.
Outputs:
    Keyword summaries, keyword correlations, and lagged correlation CSV reports
    in outputs/reports/.
"""

from __future__ import annotations
import argparse
import unicodedata
from pathlib import Path
from typing import Sequence
from scipy.stats import pearsonr
import pandas as pd
from merge_trends_data import DEFAULT_INFLUENZA, DEFAULT_TRENDS, PROJECT_ROOT, merge_datasets


DEFAULT_CONTROL_KEYWORDS = ("tenis", "vreme sutra", "recept za kolac")
DEFAULT_REPORT_DIR = PROJECT_ROOT / "outputs" / "reports"


def _normalise(text: str) -> str:
    """Return casefolded string without diacritics for matching."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return stripped.casefold()


def _filter_keywords(all_keywords: Sequence[str], controls: Sequence[str]) -> list[str]:
    """Exclude control keywords (accent-insensitive)."""
    control_lookup = {_normalise(ctrl) for ctrl in controls}
    return [
        kw
        for kw in all_keywords
        if _normalise(kw) not in control_lookup
    ]


def _safe_corr(series_x: pd.Series, series_y: pd.Series) -> float:
    """Return Pearson correlation, guarding against zero-variance inputs."""
    if series_x.std(skipna=True) == 0 or series_y.std(skipna=True) == 0:
        return float("nan")
    return series_x.corr(series_y)


def compute_keyword_correlations(df: pd.DataFrame, keywords: list[str]) -> pd.DataFrame:
    """Compute Pearson correlations (r, p) of keywords vs. INF_ALL."""
    results = []
    for kw in keywords:
        pair = df[[kw, "INF_ALL"]].dropna()
        if pair.empty:
            continue
        r, p = pearsonr(pair[kw], pair["INF_ALL"])
        results.append({"keyword": kw, "r": r, "p_value": p, "n": len(pair)})

    corr_df = pd.DataFrame(results).sort_values("r", ascending=False)
    return corr_df.set_index("keyword")


def compute_lagged_correlations(
    df: pd.DataFrame,
    signal: pd.Series,
    target: str = "INF_ALL",
    max_lag: int = 8,
) -> pd.DataFrame:
    """Compute Pearson correlations between signal and target across lags."""
    if target not in df.columns:
        return pd.DataFrame(columns=["lag", "correlation"]).set_index("lag")

    results: list[tuple[int, float]] = []
    target_series = df[target]

    for lag in range(-max_lag, max_lag + 1):
        if lag > 0:
            aligned = pd.DataFrame(
                {"signal": signal.iloc[:-lag], "target": target_series.iloc[lag:]},
                index=signal.index[:-lag],
            )
        elif lag < 0:
            aligned = pd.DataFrame(
                {"signal": signal.iloc[-lag:], "target": target_series.iloc[:lag]},
                index=signal.index[-lag:],
            )
        else:
            aligned = pd.DataFrame({"signal": signal, "target": target_series})

        aligned = aligned.dropna()
        corr = _safe_corr(aligned["signal"], aligned["target"]) if not aligned.empty else float("nan")
        results.append((lag, corr))

    return pd.DataFrame(results, columns=["lag", "correlation"]).set_index("lag")


def summarise_keywords(
    merged_wide: pd.DataFrame,
    keywords: list[str],
) -> pd.DataFrame:
    """Provide descriptive statistics for keywords."""
    stats = []
    for kw in keywords:
        series = merged_wide[kw]
        stats.append(
            {
                "keyword": kw,
                "mean": series.mean(skipna=True),
                "median": series.median(skipna=True),
                "std_dev": series.std(skipna=True),
                "observations": series.count(),
            }
        )
    return pd.DataFrame(stats).set_index("keyword")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize influenza cases vs. Google Trends keywords (excluding controls)."
    )
    parser.add_argument("--trends", type=Path, default=DEFAULT_TRENDS, help="Google Trends CSV path.")
    parser.add_argument(
        "--influenza",
        type=Path,
        default=DEFAULT_INFLUENZA,
        help="Influenza surveillance Excel path.",
    )
    parser.add_argument(
        "--controls",
        type=str,
        nargs="*",
        default=list(DEFAULT_CONTROL_KEYWORDS),
        help="Control keywords to exclude from analysis.",
    )
    parser.add_argument(
        "--max-lag",
        type=int,
        default=8,
        help="Maximum absolute lag (in weeks) for lagged correlations.",
    )
    parser.add_argument(
        "--out-summary",
        type=Path,
        default=DEFAULT_REPORT_DIR / "keyword_summary.csv",
        help="Output CSV path for keyword descriptive statistics.",
    )
    parser.add_argument(
        "--out-correlations",
        type=Path,
        default=DEFAULT_REPORT_DIR / "keyword_correlations.csv",
        help="Output CSV path for keyword correlations.",
    )
    parser.add_argument(
        "--out-lag",
        type=Path,
        default=DEFAULT_REPORT_DIR / "lagged_correlations.csv",
        help="Output CSV path for lagged correlations of aggregate signal.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    result = merge_datasets(args.trends, args.influenza, keywords=None)
    merged = result.merged_wide.sort_values("date").reset_index(drop=True)

    keyword_candidates = [
        col
        for col in merged.columns
        if col
        not in {"ISO_YEAR", "ISO_WEEK", "date", "INF_ALL", "ILI_ACTIVITY"}
        and merged[col].dtype.kind in {"i", "u", "f"}
    ]

    if not keyword_candidates:
        print("No Google Trends keywords available in merged dataset.")
        return

    keywords = _filter_keywords(keyword_candidates, args.controls)
    if not keywords:
        print("No keywords remaining after excluding controls.")
        return

    print("Keywords included in analysis (excluding controls):")
    for kw in keywords:
        print(f"  - {kw}")

    # Descriptive statistics
    keyword_stats = summarise_keywords(merged, keywords)
    args.out_summary.parent.mkdir(parents=True, exist_ok=True)
    keyword_stats.to_csv(args.out_summary)
    print(f"\nSaved keyword summary statistics to {args.out_summary}")

    # Correlations (r, p)
    correlations = compute_keyword_correlations(merged, keywords)
    args.out_correlations.parent.mkdir(parents=True, exist_ok=True)
    correlations.to_csv(args.out_correlations)
    print(f"Saved keyword correlations to {args.out_correlations}")

    print("\nTop correlations (INF_ALL vs. Google Trends):")
    for kw, row in correlations.head(10).iterrows():
        print(f"  {kw:<25} r = {row['r']:.3f}, p = {row['p_value']:.3e}, n = {row['n']:.1f}")

    # Aggregate signal (mean across all keywords)
    merged["aggregate_trend"] = merged[keywords].mean(axis=1, skipna=True)
    subset = merged[["aggregate_trend", "INF_ALL"]].dropna()
    if not subset.empty:
        r_agg, p_agg = pearsonr(subset["aggregate_trend"], subset["INF_ALL"])
        print(f"\nAggregate trend vs INF_ALL: r = {r_agg:.3f}, p = {p_agg:.3e}, n = {len(subset)}")

    # === Aggregate signal only for TOP 3 keywords ===
    top3_keywords = ["virus gripa", "grip", "simptomi gripa"]
    top3_cols = [kw for kw in top3_keywords if kw in merged.columns]
    if top3_cols:
        merged["aggregate_top3"] = merged[top3_cols].mean(axis=1, skipna=True)
        subset_top3 = merged[["aggregate_top3", "INF_ALL"]].dropna()
        if not subset_top3.empty:
            r_top3, p_top3 = pearsonr(subset_top3["aggregate_top3"], subset_top3["INF_ALL"])
            print(f"\nAggregate of top 3 keywords vs INF_ALL: r = {r_top3:.3f}, p = {p_top3:.3e}, n = {len(subset_top3)}")

    # Lagged correlations for aggregate
    lagged = compute_lagged_correlations(
        merged,
        merged["aggregate_trend"],
        target="INF_ALL",
        max_lag=args.max_lag,
    )
    args.out_lag.parent.mkdir(parents=True, exist_ok=True)
    lagged.to_csv(args.out_lag)
    best_lag = lagged["correlation"].idxmax()
    best_corr = lagged.loc[best_lag, "correlation"]
    print(f"\nSaved lagged correlations to {args.out_lag}")
    print(f"Best lag: {best_lag} weeks (correlation {best_corr: .3f})")


if __name__ == "__main__":
    main()
