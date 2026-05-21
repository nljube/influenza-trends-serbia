"""Merge Google Trends weekly data with influenza surveillance data for Serbia."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

DEFAULT_TRENDS = PROCESSED_DATA_DIR / "google_trends_weekly_serbia_2013_2025.csv"
DEFAULT_INFLUENZA = RAW_DATA_DIR / "DataExport_100625.xlsx"
DEFAULT_OUTPUT_LONG = PROCESSED_DATA_DIR / "merged_trends_influenza_long.csv"
DEFAULT_OUTPUT_WIDE = PROCESSED_DATA_DIR / "merged_trends_influenza_wide.csv"


def iso_week_start(year: pd.Series, week: pd.Series) -> pd.Series:
    """Convert ISO (year, week) to a pandas datetime (Monday of that ISO week)."""
    year_str = year.astype(int).astype(str)
    week_str = week.astype(int).astype(str).str.zfill(2)
    return pd.to_datetime(year_str + "-W" + week_str + "-1", format="%G-W%V-%u")


def load_trends(trends_path: Path, keywords: Iterable[str] | None = None) -> pd.DataFrame:
    """Load Google Trends weekly data and optionally filter keywords."""
    trends = pd.read_csv(trends_path)

    trends["ISO_YEAR"] = pd.to_numeric(trends["ISO_YEAR"], errors="coerce")
    trends["ISO_WEEK"] = pd.to_numeric(trends["ISO_WEEK"], errors="coerce")
    trends["trend_value"] = pd.to_numeric(trends["trend_value"], errors="coerce")

    trends = trends.dropna(subset=["ISO_YEAR", "ISO_WEEK", "trend_value"]).copy()
    trends["ISO_YEAR"] = trends["ISO_YEAR"].astype(int)
    trends["ISO_WEEK"] = trends["ISO_WEEK"].astype(int)
    trends["date"] = iso_week_start(trends["ISO_YEAR"], trends["ISO_WEEK"])

    if keywords:
        lookup = {kw.lower() for kw in keywords}
        trends = trends[trends["keyword"].str.lower().isin(lookup)]

    return trends.sort_values(["date", "keyword"])


def load_influenza_cases(cases_path: Path) -> pd.DataFrame:
    """Load aggregated influenza counts per ISO week for Serbia."""
    cases = pd.read_excel(cases_path, sheet_name=0)
    mask_serbia = cases["COUNTRY/AREA/TERRITORY"].str.lower().fillna("") == "serbia"
    cases = cases[mask_serbia].copy()

    cases["ISO_YEAR"] = pd.to_numeric(cases["ISO_YEAR"], errors="coerce").astype(int)
    cases["ISO_WEEK"] = pd.to_numeric(cases["ISO_WEEK"], errors="coerce").astype(int)

    aggregated = (
        cases.groupby(["ISO_YEAR", "ISO_WEEK"], as_index=False)
        .agg(
            {
                "INF_ALL": lambda s: s.sum(min_count=1),
                "ILI_ACTIVITY": "max",
            }
        )
        .sort_values(["ISO_YEAR", "ISO_WEEK"])
    )

    aggregated["date"] = iso_week_start(aggregated["ISO_YEAR"], aggregated["ISO_WEEK"])
    return aggregated.sort_values("date")


def build_trends_wide(trends: pd.DataFrame) -> pd.DataFrame:
    """Pivot keywords into separate columns (wide format)."""
    grouped = (
        trends.groupby(["ISO_YEAR", "ISO_WEEK", "date", "keyword"], as_index=False)["trend_value"]
        .mean()
    )

    wide = (
        grouped.pivot_table(
            index=["ISO_YEAR", "ISO_WEEK", "date"],
            columns="keyword",
            values="trend_value",
        )
        .reset_index()
        .sort_values("date")
    )

    wide.columns = [col if isinstance(col, str) else col[1] for col in wide.columns]
    return wide


@dataclass(frozen=True)
class MergeResult:
    trends_long: pd.DataFrame
    trends_wide: pd.DataFrame
    influenza: pd.DataFrame
    merged_wide: pd.DataFrame


def merge_datasets(
    trends_path: Path,
    influenza_path: Path,
    keywords: Sequence[str] | None = None,
) -> MergeResult:
    """Merge Google Trends data with influenza surveillance data by ISO week."""
    trends = load_trends(trends_path, keywords=keywords)
    influenza = load_influenza_cases(influenza_path)

    wide = build_trends_wide(trends)
    merged_wide = pd.merge(
        wide,
        influenza,
        on=["ISO_YEAR", "ISO_WEEK", "date"],
        how="left",
        suffixes=("", "_cases"),
    )

    trends_long = pd.merge(
        trends,
        influenza,
        on=["ISO_YEAR", "ISO_WEEK", "date"],
        how="left",
        suffixes=("", "_cases"),
    ).sort_values(["keyword", "date"])

    return MergeResult(
        trends_long=trends_long,
        trends_wide=wide,
        influenza=influenza,
        merged_wide=merged_wide,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge Google Trends weekly data with influenza counts for Serbia."
    )
    parser.add_argument("--trends", type=Path, default=DEFAULT_TRENDS, help="Google Trends CSV path.")
    parser.add_argument(
        "--influenza",
        type=Path,
        default=DEFAULT_INFLUENZA,
        help="Influenza surveillance Excel path.",
    )
    parser.add_argument(
        "--keywords",
        type=str,
        nargs="*",
        help="Optional list of keywords to keep in the Google Trends dataset.",
    )
    parser.add_argument(
        "--out-long",
        type=Path,
        default=DEFAULT_OUTPUT_LONG,
        help="Output CSV (long format).",
    )
    parser.add_argument(
        "--out-wide",
        type=Path,
        default=DEFAULT_OUTPUT_WIDE,
        help="Output CSV (wide format).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    result = merge_datasets(args.trends, args.influenza, args.keywords)

    args.out_long.parent.mkdir(parents=True, exist_ok=True)
    args.out_wide.parent.mkdir(parents=True, exist_ok=True)
    result.trends_long.to_csv(args.out_long, index=False)
    result.merged_wide.to_csv(args.out_wide, index=False)

    print(f"Saved long format to: {args.out_long}")
    print(f"Saved wide format to: {args.out_wide}")

    keyword_count = result.trends_long["keyword"].nunique()
    trend_rows = len(result.trends_long)
    print(f"Google Trends rows: {trend_rows} across {keyword_count} keywords.")

    trends_range = (
        result.trends_long["date"].min().date(),
        result.trends_long["date"].max().date(),
    )
    print(f"Google Trends date range: {trends_range[0]} -> {trends_range[1]}")

    inf_with_data = result.influenza.dropna(subset=["INF_ALL"])
    if inf_with_data.empty:
        print("Influenza dataset has no weeks with INF_ALL values.")
    else:
        inf_range = (inf_with_data["date"].min().date(), inf_with_data["date"].max().date())
        print(f"INF_ALL date range: {inf_range[0]} -> {inf_range[1]}")
        print(f"Weeks with INF_ALL data: {len(inf_with_data)}")


if __name__ == "__main__":
    main()
