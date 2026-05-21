"""Analyze exploratory relationships between Google Trends and influenza cases.

Inputs:
    Processed Google Trends CSV and influenza surveillance Excel data.
Outputs:
    Printed correlation summaries and PNG figures in outputs/figures/.
"""

from __future__ import annotations

import argparse
import unicodedata
from pathlib import Path
from typing import Iterable, Tuple

import matplotlib.pyplot as plt
import pandas as pd

from merge_trends_data import DEFAULT_INFLUENZA, DEFAULT_TRENDS, PROJECT_ROOT, merge_datasets


DEFAULT_SAVE_DIR = PROJECT_ROOT / "outputs" / "figures"


def _normalise(text: str) -> str:
    """Return a lowercase string without diacritics for fuzzy matching."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return stripped.casefold()


def _match_column(columns: Iterable[str], target: str) -> str | None:
    """Try to find a column that matches target (case-insensitive, ignoring accents)."""
    normalised = {_normalise(col): col for col in columns}
    return normalised.get(_normalise(target))


def compute_correlations(merged_wide: pd.DataFrame, target: str = "INF_ALL") -> pd.Series:
    """Compute Pearson correlations between Google Trends columns and target."""
    if target not in merged_wide.columns:
        return pd.Series(dtype=float)

    numeric_cols = [
        col
        for col in merged_wide.columns
        if col not in {"ISO_YEAR", "ISO_WEEK", "date", "ILI_ACTIVITY", target}
        and merged_wide[col].dtype.kind in {"i", "u", "f"}
    ]

    if not numeric_cols:
        return pd.Series(dtype=float)

    frame = merged_wide.dropna(subset=[target])[numeric_cols + [target]]
    if frame.empty:
        return pd.Series(dtype=float)

    correlations = frame.corr(numeric_only=True)[target].drop(target)
    return correlations.sort_values(ascending=False)


def plot_correlations(
    corr_series: pd.Series,
    top_n: int | None = None,
) -> Tuple[plt.Figure, plt.Axes] | Tuple[None, None]:
    """Plot a horizontal bar chart of correlations."""
    corr_series = corr_series.dropna()
    if corr_series.empty:
        return None, None

    data = corr_series.head(top_n) if top_n else corr_series
    data = data.sort_values()
    fig_height = max(3.0, 0.4 * len(data) + 1.5)
    fig, ax = plt.subplots(figsize=(8, fig_height))
    ax.barh(data.index, data.values, color="steelblue")
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Pearson r")
    ax.set_title("INF_ALL vs. Google Trends correlations")
    ax.grid(axis="x", linestyle="--", alpha=0.5)
    fig.tight_layout()
    return fig, ax


def plot_trend_vs_cases(
    merged_wide: pd.DataFrame,
    keyword: str,
    rolling_window: int | None = None,
) -> Tuple[plt.Figure, plt.Axes, plt.Axes] | Tuple[None, None, None]:
    """Plot influenza cases and Google Trends time series for a given keyword."""
    column = _match_column(merged_wide.columns, keyword)
    if column is None:
        print(f"Keyword '{keyword}' not found in merged dataset.")
        return None, None, None

    series = merged_wide[["date", "INF_ALL", column]].dropna(subset=["date"])
    series = series.sort_values("date")

    if rolling_window and rolling_window > 1:
        series["INF_ALL"] = series["INF_ALL"].rolling(rolling_window, min_periods=1).mean()
        series[column] = series[column].rolling(rolling_window, min_periods=1).mean()

    fig, ax_cases = plt.subplots(figsize=(14, 6))
    ax_cases.plot(series["date"], series["INF_ALL"], color="tab:red", label="INF_ALL")
    ax_cases.set_ylabel("Confirmed cases (INF_ALL)", color="tab:red")

    ax_trends = ax_cases.twinx()
    ax_trends.plot(series["date"], series[column], color="tab:blue", label=f"Google Trends: {column}")
    ax_trends.set_ylabel("Google Trends (0-100)", color="tab:blue")

    ax_cases.set_xlabel("Date")
    ax_cases.set_title(f"Influenza cases vs. Google Trends for '{column}'")
    fig.tight_layout()
    return fig, ax_cases, ax_trends


def plot_seasonal_profile(
    trends_long: pd.DataFrame,
    keyword: str,
) -> Tuple[plt.Figure, plt.Axes] | Tuple[None, None]:
    """Plot mean weekly profile (with interquartile range) for a keyword."""
    mask = trends_long["keyword"].apply(lambda value: _normalise(value) == _normalise(keyword))
    subset = trends_long.loc[mask].copy()
    if subset.empty:
        print(f"No trends data available for keyword '{keyword}'.")
        return None, None

    subset = subset.dropna(subset=["ISO_WEEK", "trend_value"])
    subset["ISO_WEEK"] = subset["ISO_WEEK"].astype(int)

    grouped = subset.groupby("ISO_WEEK")["trend_value"]
    mean = grouped.mean()
    q25 = grouped.quantile(0.25)
    q75 = grouped.quantile(0.75)

    weeks = mean.index
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.fill_between(weeks, q25, q75, color="skyblue", alpha=0.3, label="Interquartile range (25-75)")
    ax.plot(weeks, mean, color="navy", linewidth=2, label="Weekly mean")

    ax.set_xlabel("ISO week")
    ax.set_ylabel("Google Trends (0-100)")
    ax.set_title(f"Seasonal profile for '{keyword}'")
    ax.set_xticks(range(1, 54, 4))
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend()
    fig.tight_layout()
    return fig, ax


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyse Google Trends vs. influenza cases with plots."
    )
    parser.add_argument("--trends", type=Path, default=DEFAULT_TRENDS, help="Google Trends CSV.")
    parser.add_argument("--influenza", type=Path, default=DEFAULT_INFLUENZA, help="Influenza Excel.")
    parser.add_argument(
        "--keywords",
        type=str,
        nargs="*",
        help="Optional list of Google Trends keywords to include.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Limit number of correlations displayed (default: sve dostupne).",
    )
    parser.add_argument(
        "--rolling-window",
        type=int,
        default=None,
        help="Optional rolling window (weeks) to smooth time series.",
    )
    parser.add_argument(
        "--save-dir",
        type=Path,
        default=DEFAULT_SAVE_DIR,
        help=f"Directory to save generated figures (PNG). Default: {DEFAULT_SAVE_DIR}",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Do not display figures interactively (useful for batch runs).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    result = merge_datasets(args.trends, args.influenza, args.keywords)
    correlations = compute_correlations(result.merged_wide)

    if correlations.empty:
        print("No correlations available (missing INF_ALL or Google Trends data).")
    else:
        display_series = correlations.head(args.top_n) if args.top_n else correlations
        print("Correlations (INF_ALL vs. Google Trends):")
        for keyword, value in display_series.items():
            print(f"  {keyword:<25} {value: .3f}")

    figures_to_show: list[plt.Figure] = []
    save_dir = args.save_dir

    fig_corr, _ = plot_correlations(correlations, top_n=args.top_n)
    if fig_corr:
        if save_dir:
            save_dir.mkdir(parents=True, exist_ok=True)
            output_path = save_dir / "correlations.png"
            fig_corr.savefig(output_path, dpi=150)
            print(f"Saved figure: {output_path}")
        if args.no_show:
            plt.close(fig_corr)
        else:
            figures_to_show.append(fig_corr)

    keyword_list = (
        result.trends_long["keyword"]
        .dropna()
        .unique()
    )
    keyword_list = sorted(keyword_list, key=_normalise)

    for kw in keyword_list:
        fig_ts, _, _ = plot_trend_vs_cases(
            result.merged_wide,
            keyword=kw,
            rolling_window=args.rolling_window,
        )
        if fig_ts:
            if save_dir:
                save_dir.mkdir(parents=True, exist_ok=True)
                ts_path = save_dir / f"time_series_{_normalise(kw)}.png"
                fig_ts.savefig(ts_path, dpi=150)
                print(f"Saved figure: {ts_path}")
            if args.no_show:
                plt.close(fig_ts)
            else:
                figures_to_show.append(fig_ts)

        fig_season, _ = plot_seasonal_profile(result.trends_long, keyword=kw)
        if fig_season:
            if save_dir:
                save_dir.mkdir(parents=True, exist_ok=True)
                season_path = save_dir / f"seasonality_{_normalise(kw)}.png"
                fig_season.savefig(season_path, dpi=150)
                print(f"Saved figure: {season_path}")
            if args.no_show:
                plt.close(fig_season)
            else:
                figures_to_show.append(fig_season)

    if figures_to_show and not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
