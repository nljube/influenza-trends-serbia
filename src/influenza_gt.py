"""Collect weekly Google Trends data for influenza-related searches in Serbia.

Inputs:
    Predefined Serbian-language keywords, Google Trends geo code RS, and the
    configured 2013-2025 time window.
Outputs:
    Raw per-keyword CSV exports in data/raw/root_exports/, a combined raw CSV in
    data/raw/, weekly processed trends in data/processed/, and a local run log in
    outputs/reports/.
"""

import time
import random
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from pytrends.request import TrendReq

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9 fallback
    ZoneInfo = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_EXPORT_DIR = PROJECT_ROOT / "data" / "raw" / "root_exports"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = PROJECT_ROOT / "outputs" / "reports"

# =====================================================
# KONFIGURACIJA
# =====================================================

keywords = [
    # Core
    "grip",
    "virus gripa",
    "simptomi gripa",
    "prehlada",
    "simptomi prehlade",
    # Simptomi
    "temperatura i bolovi",
    "kašalj",
    "bol u grlu",
    "curenje nosa",
    # Lečenje
    "lek za grip",
    "sirup za kašalj",
    "čaj za grip",
    # Prevencija
    "vakcina protiv gripa",
    "vitamin c",
    # Negativne kontrole
    "tenis",
    "vreme sutra",
    "recept za kolač",
]

country = "RS"
start_year = 2013
end_year = 2025

WINDOW_YEARS = 3
OVERLAP_WEEKS = 26
REQUEST_DELAY = 80  # duža osnovna pauza između upita
MAX_RETRIES = 3
COOLDOWN_429 = 600  # 10 minuta čekanja kod 429
LOG_FILE = REPORT_DIR / "trends_log.txt"


def _compute_tz_offset_minutes(default: int = 120) -> int:
    """Vraća ofset u minutima za Europe/Belgrade ili zadaje podrazumevani."""
    if ZoneInfo is None:
        return default
    try:
        belgrade = ZoneInfo("Europe/Belgrade")
    except Exception:
        return default

    now = datetime.now(belgrade)
    offset = now.utcoffset()
    if not offset:
        return default
    return int(offset.total_seconds() // 60)


TZ_OFFSET_MINUTES = _compute_tz_offset_minutes()

# =====================================================
# FUNKCIJE
# =====================================================


def log_message(message: str):
    """Upisuje poruku i u terminal i u log fajl (UTF-8 kompatibilno, bez simbola)."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    text = f"{timestamp} | {message}"
    print(text)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8", errors="ignore") as log:
        log.write(text + "\n")


def _sanitize_keyword(keyword: str) -> str:
    """Pretvara ključnu reč u stabilno ASCII ime fajla."""
    normalized = unicodedata.normalize("NFKD", keyword)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = [ch if ch.isalnum() else "_" for ch in ascii_only.lower()]
    collapsed = "_".join(filter(None, "".join(cleaned).split("_")))
    return collapsed or "keyword"


def _build_time_windows(
    start_year: int, end_year: int, window_years: int, overlap_weeks: int
) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
    start = pd.Timestamp(f"{start_year}-01-01")
    end = pd.Timestamp(f"{end_year}-01-01")
    windows: List[Tuple[pd.Timestamp, pd.Timestamp]] = []
    current_start = start
    while current_start < end:
        current_end = min(current_start + pd.DateOffset(years=window_years), end)
        windows.append((current_start, current_end))
        if current_end == end:
            break
        current_start = current_end - pd.DateOffset(weeks=overlap_weeks)
    return windows


def _fetch_window(pytrends: TrendReq, keyword: str, timeframe: str) -> pd.Series:
    """Preuzima podatke za jedan vremenski prozor."""
    log_message(f"  -> {keyword}: {timeframe}")
    pytrends.build_payload([keyword], geo=country, timeframe=timeframe)
    window = pytrends.interest_over_time()
    if window.empty:
        return pd.Series(dtype="float64")
    window = window.loc[~window["isPartial"], keyword].astype("float64")
    window.name = "trend_value"
    return window


def _scale_window(
    accumulated: pd.Series, new_window: pd.Series
) -> Tuple[pd.Series, float]:
    """Skalira novi prozor prema prethodnom, na osnovu preklapanja."""
    overlap_index = accumulated.index.intersection(new_window.index)
    if overlap_index.empty:
        return new_window, 1.0

    overlap_acc = accumulated.loc[overlap_index]
    overlap_new = new_window.loc[overlap_index]
    valid_mask = (overlap_acc > 0) & (overlap_new > 0)
    if valid_mask.any():
        scale_factor = overlap_acc[valid_mask].mean() / overlap_new[valid_mask].mean()
    else:
        denom = overlap_new.mean()
        scale_factor = overlap_acc.mean() / denom if denom else 1.0

    scale_factor = (
        1.0 if not pd.notna(scale_factor) or scale_factor <= 0 else scale_factor
    )
    scale_factor = max(min(scale_factor, 10.0), 0.1)

    adjusted = new_window * scale_factor
    adjusted = adjusted[~adjusted.index.isin(accumulated.index)]
    return adjusted, scale_factor


def get_weekly_trends(keyword: str) -> pd.Series:
    """Preuzima i spaja sve vremenske prozore za zadatu ključnu reč."""
    windows = _build_time_windows(start_year, end_year, WINDOW_YEARS, OVERLAP_WEEKS)
    combined = pd.Series(dtype="float64")

    for start_ts, end_ts in windows:
        timeframe = f"{start_ts.date()} {end_ts.date()}"
        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                pytrends = TrendReq(hl="sr", tz=TZ_OFFSET_MINUTES)
                window_series = _fetch_window(pytrends, keyword, timeframe)
                break
            except Exception as error:
                last_error = error
                log_message(f"Upozorenje: greška za {keyword} ({timeframe}), pokušaj {attempt}: {error}")
                if "429" in str(error):
                    log_message("Blokada (429) – čeka se i resetuje sesija...")
                    time.sleep(COOLDOWN_429 + random.uniform(10, 164))
                else:
                    time.sleep(REQUEST_DELAY + random.uniform(-5, 87))
        else:
            log_message(f"Preskačem interval {timeframe} zbog ponovljenih grešaka: {last_error}")
            continue

        if window_series.empty:
            log_message(f"Prazni podaci za {keyword} ({timeframe})")
            time.sleep(REQUEST_DELAY + random.uniform(-5, 38))
            continue

        if combined.empty:
            combined = window_series.copy()
        else:
            adjusted, _ = _scale_window(combined, window_series)
            if not adjusted.empty:
                combined = pd.concat([combined, adjusted])

        time.sleep(REQUEST_DELAY + random.uniform(-10, 26))
        time.sleep(random.uniform(5, 15))  # dodatna kratka pauza

    combined = combined.sort_index()
    combined.name = "trend_value"
    return combined


# =====================================================
# GLAVNI DEO
# =====================================================

log_message("===== POKRETANJE GOOGLE TRENDS ANALIZE (UTF-8, ASCII SAFE) =====")
log_message(f"Konfigurisani tz ofset: {TZ_OFFSET_MINUTES} minuta")
RAW_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
all_trends: Dict[str, pd.DataFrame] = {}

for kw in keywords:
    log_message(f"\n=== Preuzimam podatke za: {kw} ===")
    series_kw = get_weekly_trends(kw)
    if series_kw.empty:
        log_message(f"Nema dostupnih podataka za {kw}, preskačem.")
        continue

    df_kw = series_kw.to_frame().reset_index().rename(columns={"index": "date"})
    df_kw["keyword"] = kw
    all_trends[kw] = df_kw

    safe_name = _sanitize_keyword(kw)
    df_kw.to_csv(RAW_EXPORT_DIR / f"partial_{safe_name}.csv", index=False)
    log_message(f"Snimljen parcijalni fajl za {kw}")
    time.sleep(REQUEST_DELAY + random.uniform(159, 283))  # duža pauza između ključnih reči

if not all_trends:
    raise SystemExit("Nema podataka za čuvanje.")

final_df = pd.concat(all_trends.values(), ignore_index=True)

final_df["date"] = pd.to_datetime(final_df["date"], utc=False)
iso_calendar = final_df["date"].dt.isocalendar()
final_df["ISO_YEAR"] = iso_calendar.year
final_df["ISO_WEEK"] = iso_calendar.week

final_df.to_csv(PROJECT_ROOT / "data" / "raw" / "google_trends_serbia_2013_2025.csv", index=False)
weekly_df = final_df.groupby(["keyword", "ISO_YEAR", "ISO_WEEK"], as_index=False)["trend_value"].mean()
weekly_df.to_csv(PROCESSED_DATA_DIR / "google_trends_weekly_serbia_2013_2025.csv", index=False)

log_message("Gotovo! Podaci uspešno preuzeti i sačuvani.")
