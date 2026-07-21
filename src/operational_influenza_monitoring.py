"""Explore operational influenza monitoring signals from Google Trends data.

Inputs:
    Processed Google Trends CSV and influenza surveillance Excel data.
Outputs:
    Console summaries of focus-keyword correlations and lag patterns for the
    full period and predefined sub-periods.
"""

from __future__ import annotations

import argparse
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from merge_trends_data import DEFAULT_INFLUENZA, DEFAULT_TRENDS, merge_datasets


FOCUS_KEYWORDS = ("grip", "virus gripa", "simptomi gripa")
DEFAULT_MAX_LAG = 8
SUBPERIODS = (
    ("2013-01-01", "2018-12-31"),
    ("2019-01-01", "2022-12-31"),
    ("2023-01-01", "2026-12-31"),
)


def _normalise(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(
        ch for ch in decomposed if unicodedata.category(ch) != "Mn"
    ).casefold()


def _match_keywords(available: Iterable[str], targets: Sequence[str]) -> dict[str, str]:
    lookup = {_normalise(col): col for col in available}
    result: dict[str, str] = {}
    for target in targets:
        col = lookup.get(_normalise(target))
        if col:
            result[target] = col
    return result


def _safe_corr(series_x: pd.Series, series_y: pd.Series) -> float:
    if series_x.std(skipna=True) == 0 or series_y.std(skipna=True) == 0:
        return float("nan")
    return series_x.corr(series_y)


def compute_lagged_correlations(
    signal: pd.Series,
    target: pd.Series,
    max_lag: int,
) -> pd.DataFrame:
    records = []
    # Shift by position via numpy arrays; a dict of index-carrying Series would be
    # realigned by label, silently undoing the lag.
    signal_values = signal.to_numpy(dtype="float64")
    target_values = target.to_numpy(dtype="float64")
    for lag in range(-max_lag, max_lag + 1):
        if lag > 0:
            shifted_signal = signal_values[:-lag]
            shifted_target = target_values[lag:]
        elif lag < 0:
            shifted_signal = signal_values[-lag:]
            shifted_target = target_values[:lag]
        else:
            shifted_signal = signal_values
            shifted_target = target_values

        aligned = pd.DataFrame(
            {"signal": shifted_signal, "target": shifted_target}
        ).dropna()
        corr = (
            _safe_corr(aligned["signal"], aligned["target"])
            if not aligned.empty
            else float("nan")
        )
        records.append((lag, corr, len(aligned)))
    return pd.DataFrame(records, columns=["lag", "correlation", "n_obs"]).set_index(
        "lag"
    )


@dataclass(frozen=True)
class LagSummary:
    best_lag: int
    correlation: float
    n_obs: int


def summarize_lags(
    data: pd.DataFrame,
    signal_cols: Sequence[str],
    max_lag: int,
) -> dict[str, LagSummary]:
    summaries: dict[str, LagSummary] = {}
    target = data["INF_ALL"]

    for key in signal_cols:
        series = data[key]
        lag_table = compute_lagged_correlations(series, target, max_lag)
        if lag_table["correlation"].notna().any():
            best_row = lag_table["correlation"].idxmax()
            summaries[key] = LagSummary(
                best_lag=best_row,
                correlation=lag_table.loc[best_row, "correlation"],
                n_obs=int(lag_table.loc[best_row, "n_obs"]),
            )
        else:
            summaries[key] = LagSummary(best_lag=0, correlation=float("nan"), n_obs=0)
    return summaries


def aggregate_top_signals(
    data: pd.DataFrame,
    focus_keys: Sequence[str],
    top_k: int,
) -> pd.Series:
    corr_map = {}
    target = data["INF_ALL"]
    for key in focus_keys:
        pair = data[[key, "INF_ALL"]].dropna()
        corr_map[key] = (
            _safe_corr(pair[key], pair["INF_ALL"]) if not pair.empty else float("nan")
        )
    ordered = sorted(
        (item for item in corr_map.items() if pd.notna(item[1])),
        key=lambda x: x[1],
        reverse=True,
    )
    selected = [name for name, _ in ordered[:top_k]]
    if not selected:
        return pd.Series(index=data.index, dtype=float)
    agg = data[selected].mean(axis=1, skipna=True)
    agg.name = "top_k_aggregate"
    return agg


def filter_period(data: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    mask = (data["date"] >= start) & (data["date"] <= end)
    return data.loc[mask].copy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Operational lag analysis for influenza trends."
    )
    parser.add_argument("--trends", type=Path, default=DEFAULT_TRENDS)
    parser.add_argument("--influenza", type=Path, default=DEFAULT_INFLUENZA)
    parser.add_argument("--max-lag", type=int, default=DEFAULT_MAX_LAG)
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of keywords to include in aggregate signal.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = merge_datasets(args.trends, args.influenza, keywords=None)
    merged = result.merged_wide.sort_values("date").reset_index(drop=True)

    available_keywords = [
        col
        for col in merged.columns
        if col not in {"ISO_YEAR", "ISO_WEEK", "date", "INF_ALL", "ILI_ACTIVITY"}
        and merged[col].dtype.kind in {"i", "u", "f"}
    ]

    keyword_map = _match_keywords(available_keywords, FOCUS_KEYWORDS)
    if len(keyword_map) < len(FOCUS_KEYWORDS):
        missing = [kw for kw in FOCUS_KEYWORDS if kw not in keyword_map]
        print("Missing keywords:", ", ".join(missing))
    tracked_cols = list(keyword_map.values())

    if not tracked_cols:
        print("No focus keywords found in dataset.")
        return

    print("Focus keywords:")
    for display, actual in keyword_map.items():
        print(f"  - {display} -> {actual}")

    aggregate = aggregate_top_signals(merged, tracked_cols, args.top_k)
    if not aggregate.empty:
        merged["top_k_aggregate"] = aggregate
        tracked_cols.append("top_k_aggregate")
        print(
            f"\nAggregate signal built from top {args.top_k} keywords based on correlations."
        )
    else:
        print("\nAggregate signal could not be computed (insufficient data).")

    print("\nOverall best lags:")
    overall = summarize_lags(merged, tracked_cols, args.max_lag)
    for key, summary in overall.items():
        print(
            f"  {key:<20} lag {summary.best_lag:>3} weeks | r = {summary.correlation: .3f} | n = {summary.n_obs}"
        )

    print("\nSub-period validation:")
    for start, end in SUBPERIODS:
        subset = filter_period(merged, start, end)
        if subset["INF_ALL"].notna().sum() < 5:
            print(f"  {start[:4]}-{end[:4]}: insufficient INF_ALL data.")
            continue
        sub_summaries = summarize_lags(subset, tracked_cols, args.max_lag)
        print(f"  {start[:4]}-{end[:4]}:")
        for key, summary in sub_summaries.items():
            print(
                f"    {key:<20} lag {summary.best_lag:>3} | r = {summary.correlation: .3f} | n = {summary.n_obs}"
            )


if __name__ == "__main__":
    main()
