"""Phase 3: PELT changepoint detection + hypothesis formation."""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import ruptures as rpt
from pathlib import Path

FIGS = Path("outputs/figures")
TABS = Path("outputs/tables")

df = pd.read_parquet("data/processed/uc1.parquet")
df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], utc=False)

# ── Hourly aggregates ─────────────────────────────────────────────────────────
df["hour_bin"] = df["TIMESTAMP"].dt.floor("h")
hourly = df.groupby("hour_bin").agg(
    cw1_comp_duty=("CW1_COMPRESSOR_RUNNING", "mean"),
    cw1_pressure_mean=("CW1_MAIN_RESERVOIR_PRESSURE", "mean"),
    cw1_pressure_std=("CW1_MAIN_RESERVOIR_PRESSURE", "std"),
    cw2_comp_duty=("CW2_COMPRESSOR_RUNNING", "mean"),
    speed_mean=("TRAIN_SPEED_ACTUAL", "mean"),
    failure_type=("TRAIN_FAILURE_TYPE", lambda x: x.value_counts().index[0]),
).reset_index()
hourly.to_csv(TABS / "hourly_aggregates.csv", index=False)

# ── PELT on CW1 duty-cycle ────────────────────────────────────────────────────
def run_pelt(signal, pen=3):
    algo = rpt.Pelt(model="rbf", jump=1).fit(signal.reshape(-1, 1))
    return algo.predict(pen=pen)

cw1_duty_signal = hourly["cw1_comp_duty"].fillna(0).values
cw1_press_signal = hourly["cw1_pressure_mean"].ffill().values
cw2_duty_signal = hourly["cw2_comp_duty"].fillna(0).values

bkps_duty  = run_pelt(cw1_duty_signal,  pen=3)
bkps_press = run_pelt(cw1_press_signal, pen=3)
bkps_cw2   = run_pelt(cw2_duty_signal,  pen=3)

def bkp_timestamps(bkps, hour_bins):
    """Convert breakpoint indices to timestamps (excluding last sentinel)."""
    return [hour_bins.iloc[min(b, len(hour_bins)-1)] for b in bkps[:-1]]

bkp_duty_ts  = bkp_timestamps(bkps_duty,  hourly["hour_bin"])
bkp_press_ts = bkp_timestamps(bkps_press, hourly["hour_bin"])
bkp_cw2_ts   = bkp_timestamps(bkps_cw2,  hourly["hour_bin"])

print("=== PELT breakpoints ===")
print(f"CW1 duty-cycle ({len(bkps_duty)-1} bkp):", bkp_duty_ts)
print(f"CW1 pressure  ({len(bkps_press)-1} bkp):", bkp_press_ts)
print(f"CW2 duty-cycle ({len(bkps_cw2)-1} bkp):", bkp_cw2_ts)

# Save breakpoints table
bkp_records = (
    [{"signal": "CW1_duty",    "breakpoint_time": t} for t in bkp_duty_ts] +
    [{"signal": "CW1_pressure","breakpoint_time": t} for t in bkp_press_ts] +
    [{"signal": "CW2_duty",    "breakpoint_time": t} for t in bkp_cw2_ts]
)
pd.DataFrame(bkp_records).to_csv(TABS / "pelt_breakpoints.csv", index=False)

# ── Figure: PELT changepoint plot ─────────────────────────────────────────────
fig, axes = plt.subplots(3, 1, figsize=(16, 10), sharex=True)

FTYPE_COLORS = {
    "No Failure": "#d4e6f1",
    "Brake System Failure": "#f9e4b7",
    "Compressor Module Failure": "#f5b7b1",
}

def add_bands(ax):
    for ftype, color in FTYPE_COLORS.items():
        mask = hourly["failure_type"] == ftype
        if not mask.any():
            continue
        starts = hourly.loc[mask & (~mask.shift(1, fill_value=False)), "hour_bin"]
        ends   = hourly.loc[mask & (~mask.shift(-1, fill_value=False)), "hour_bin"]
        for s, e in zip(starts, ends):
            ax.axvspan(s, e, color=color, alpha=0.25, linewidth=0)

datasets = [
    (hourly["cw1_comp_duty"],    bkp_duty_ts,  "CW1 Compressor Duty-Cycle (hourly)",    "#e74c3c"),
    (hourly["cw1_pressure_mean"],bkp_press_ts, "CW1 Main Reservoir Pressure mean (bar)","#8e44ad"),
    (hourly["cw2_comp_duty"],    bkp_cw2_ts,   "CW2 Compressor Duty-Cycle (hourly)",    "#3498db"),
]
for ax, (series, bkps, label, color) in zip(axes, datasets):
    add_bands(ax)
    ax.plot(hourly["hour_bin"], series, lw=1, color=color)
    for b in bkps:
        ax.axvline(b, color="black", lw=1.2, linestyle="--", alpha=0.7)
    ax.set_ylabel(label, fontsize=8)

axes[0].set_title("PELT changepoint detection on hourly aggregates (penalty=3)", fontsize=10)
fig.tight_layout()
fig.savefig(FIGS / "08_pelt_changepoints.png", dpi=150)
plt.close()

# ── Quantified hypothesis summary ────────────────────────────────────────────
cmf_mask_h = hourly["failure_type"] == "Compressor Module Failure"
first_cmf_ts = hourly.loc[cmf_mask_h, "hour_bin"].min()

# Measure duty-cycle: last 3 normal days vs final 12h before CMF on Feb 24
# "normal" period = Feb 17-23, no CMF
normal_h = hourly[(hourly["failure_type"] == "No Failure") &
                  (hourly["hour_bin"] < pd.Timestamp("2025-02-23 00:00", tz="Europe/Vienna"))]
pre_fail_h = hourly[
    (hourly["hour_bin"] >= first_cmf_ts - pd.Timedelta("12h")) &
    (hourly["hour_bin"] < first_cmf_ts)
]

print("\n=== Hypothesis quantification ===")
print(f"Normal CW1 duty-cycle   mean: {normal_h['cw1_comp_duty'].mean():.3f}")
print(f"Pre-fail CW1 duty-cycle mean: {pre_fail_h['cw1_comp_duty'].mean():.3f}")
print(f"Normal CW1 pressure     mean: {normal_h['cw1_pressure_mean'].mean():.3f} bar")
print(f"Pre-fail CW1 pressure   mean: {pre_fail_h['cw1_pressure_mean'].mean():.3f} bar")
print(f"Normal CW2 duty-cycle   mean: {normal_h['cw2_comp_duty'].mean():.3f}")
print(f"Pre-fail CW2 duty-cycle mean: {pre_fail_h['cw2_comp_duty'].mean():.3f}")

hyp = pd.DataFrame([
    {"metric": "CW1 duty-cycle (normal)",    "value": normal_h['cw1_comp_duty'].mean()},
    {"metric": "CW1 duty-cycle (pre-fail)",  "value": pre_fail_h['cw1_comp_duty'].mean()},
    {"metric": "CW1 pressure mean (normal)",  "value": normal_h['cw1_pressure_mean'].mean()},
    {"metric": "CW1 pressure mean (pre-fail)","value": pre_fail_h['cw1_pressure_mean'].mean()},
    {"metric": "CW2 duty-cycle (normal)",    "value": normal_h['cw2_comp_duty'].mean()},
    {"metric": "CW2 duty-cycle (pre-fail)",  "value": pre_fail_h['cw2_comp_duty'].mean()},
])
hyp.to_csv(TABS / "hypothesis_quantification.csv", index=False)

# Earliest breakpoint in CW1 signals (relative to first CMF on Feb 24)
all_cw1_bkps = sorted(bkp_duty_ts + bkp_press_ts)
pre_cmf_bkps = [t for t in all_cw1_bkps if t < first_cmf_ts]
if pre_cmf_bkps:
    earliest = min(pre_cmf_bkps)
    lead_time = (first_cmf_ts - earliest).total_seconds() / 3600
    print(f"\nEarliest CW1 breakpoint before Feb-24 CMF: {earliest}  (lead time {lead_time:.1f} h)")
else:
    print("\nNo CW1 breakpoints found before first CMF.")

print("\nPhase 3 complete.")
