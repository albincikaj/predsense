"""Phase 4 preparation: export CSV for Predsense labeling (no TRAIN_FAILURE_TYPE)."""

import pandas as pd
from pathlib import Path

OUT = Path("data/exports/uc1_for_labeling.csv")
df = pd.read_parquet("data/processed/uc1.parquet")
df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], utc=False)

# Export only original 7 columns minus the failure type label
cols = [
    "TIMESTAMP",
    "CW1_PNEUMATIC_BRAKE_ACTIVE",
    "CW1_COMPRESSOR_RUNNING",
    "CW1_MAIN_RESERVOIR_PRESSURE",
    "CW2_COMPRESSOR_RUNNING",
    "CW2_PNEUMATIC_BRAKE_ACTIVE",
    "TRAIN_SPEED_ACTUAL",
]
export_df = df[cols].copy()
# Format timestamp as ISO 8601 without timezone offset for max compatibility
export_df["TIMESTAMP"] = export_df["TIMESTAMP"].dt.strftime("%Y-%m-%d %H:%M:%S")

export_df.to_csv(OUT, index=False)
print(f"Exported {len(export_df):,} rows to {OUT}  ({OUT.stat().st_size / 1e6:.1f} MB)")
print(export_df.head(3))
