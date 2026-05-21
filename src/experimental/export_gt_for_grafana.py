# export_gt_for_grafana.py
import pandas as pd
from pathlib import Path

from pytrends.request import TrendReq

PROJECT_ROOT = Path(__file__).resolve().parents[2]

KEYWORDS = [
    "grip",
    "virus gripa",
    "simptomi gripa",
    "temperatura",
    "kašalj",
    "bol u grlu",
    "bolovi u kostima i mišićima"
]

pytrends = TrendReq(hl="sr", tz=120)
pytrends.build_payload(KEYWORDS, geo="RS", timeframe="now 5-y")
df = pytrends.interest_over_time().reset_index()

# datetime
df["date"] = pd.to_datetime(df["date"])
df = df.set_index("date")

# izbaci pytrends flag
if "isPartial" in df.columns:
    df = df.drop(columns=["isPartial"])

# epidemiološka nedelja (ponedeljak)
df_weekly = df.resample("W-MON").mean()

# EXPORT (date ide kao kolona)
output_path = PROJECT_ROOT / "outputs" / "reports" / "google_trends_influenza_rs.csv"
output_path.parent.mkdir(parents=True, exist_ok=True)
df_weekly.reset_index().to_csv(
    output_path,
    index=False
)
