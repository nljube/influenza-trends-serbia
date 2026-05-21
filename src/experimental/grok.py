from scipy.stats import pearsonr
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "merged_trends_influenza_wide.csv")
for kw in ["virus gripa", "grip", "simptomi gripa"]:
    corr, p_value = pearsonr(df[kw].dropna(), df["INF_ALL"].dropna())
    print(f"{kw}: r={corr:.3f}, p={p_value:.3e}")
