"""Phase 1: Ingest and normalize use_case_1.xlsx into uc1.parquet."""

import pandas as pd
import numpy as np
from pathlib import Path

RAW = Path("data/raw/use_case_1.xlsx")
OUT_PARQUET = Path("data/processed/uc1.parquet")
OUT_QUALITY = Path("outputs/tables/data_quality.csv")

# ── Load ─────────────────────────────────────────────────────────────────────
print("Loading Excel file …")
df = pd.read_excel(RAW, engine="openpyxl")
print(f"  Raw shape: {df.shape}")

# ── Sort and reset ────────────────────────────────────────────────────────────
df = df.sort_values("TIMESTAMP").reset_index(drop=True)

# ── Timezone ──────────────────────────────────────────────────────────────────
df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"])
if df["TIMESTAMP"].dt.tz is None:
    df["TIMESTAMP"] = df["TIMESTAMP"].dt.tz_localize("Europe/Vienna", ambiguous="infer", nonexistent="shift_forward")
else:
    df["TIMESTAMP"] = df["TIMESTAMP"].dt.tz_convert("Europe/Vienna")

# ── Boolean columns ───────────────────────────────────────────────────────────
bool_cols = [
    "CW1_PNEUMATIC_BRAKE_ACTIVE",
    "CW1_COMPRESSOR_RUNNING",
    "CW2_COMPRESSOR_RUNNING",
    "CW2_PNEUMATIC_BRAKE_ACTIVE",
]
for c in bool_cols:
    df[c] = df[c].astype(bool)

# ── Derived columns ───────────────────────────────────────────────────────────
df["date"] = df["TIMESTAMP"].dt.date
df["hour"] = df["TIMESTAMP"].dt.hour
df["minute_of_day"] = df["TIMESTAMP"].dt.hour * 60 + df["TIMESTAMP"].dt.minute
df["is_moving"] = df["TRAIN_SPEED_ACTUAL"] > 0.01

# Pre-failure flags: samples before each Compressor Module Failure block
cmf_mask = df["TRAIN_FAILURE_TYPE"] == "Compressor Module Failure"
cmf_times = df.loc[cmf_mask, "TIMESTAMP"]

# The main failure block starts on Feb 24; define lead-time windows relative
# to the FIRST Compressor Module Failure timestamp overall
if cmf_mask.any():
    first_cmf = cmf_times.min()
    df["pre_failure_24h"] = (df["TIMESTAMP"] >= first_cmf - pd.Timedelta("24h")) & (~cmf_mask)
    df["pre_failure_12h"] = (df["TIMESTAMP"] >= first_cmf - pd.Timedelta("12h")) & (~cmf_mask)
    df["pre_failure_6h"]  = (df["TIMESTAMP"] >= first_cmf - pd.Timedelta("6h"))  & (~cmf_mask)
    df["pre_failure_1h"]  = (df["TIMESTAMP"] >= first_cmf - pd.Timedelta("1h"))  & (~cmf_mask)
else:
    for col in ["pre_failure_24h", "pre_failure_12h", "pre_failure_6h", "pre_failure_1h"]:
        df[col] = False

# ── Save parquet ──────────────────────────────────────────────────────────────
df.to_parquet(OUT_PARQUET, index=False)
print(f"  Saved parquet: {OUT_PARQUET}  ({len(df):,} rows, {len(df.columns)} cols)")

# ── Data quality report ───────────────────────────────────────────────────────
rows_per_day = df.groupby("date").size().rename("row_count")

# Timestamp gaps (seconds) — find gaps larger than the typical cadence
ts_diff = df["TIMESTAMP"].diff().dt.total_seconds().dropna()
typical_cadence = ts_diff.median()
gaps = ts_diff[ts_diff > typical_cadence * 5]
gap_count = len(gaps)
max_gap_s = gaps.max() if gap_count > 0 else 0.0

# Duplicate timestamps
dup_count = df["TIMESTAMP"].duplicated().sum()

quality_rows = []
for day, cnt in rows_per_day.items():
    quality_rows.append({
        "date": day,
        "row_count": cnt,
        "duplicate_timestamps": dup_count,
        "gap_count_gt5x_median": gap_count,
        "max_gap_seconds": round(max_gap_s, 1),
        "median_cadence_seconds": round(typical_cadence, 3),
    })
quality_df = pd.DataFrame(quality_rows)
quality_df.to_csv(OUT_QUALITY, index=False)
print(f"  Data quality saved: {OUT_QUALITY}")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\nColumn dtypes:")
print(df.dtypes)
print("\nFailure type counts:")
print(df["TRAIN_FAILURE_TYPE"].value_counts())
print(f"\nTime span: {df['TIMESTAMP'].min()} to {df['TIMESTAMP'].max()}")
print(f"Missing values:\n{df.isnull().sum()}")
