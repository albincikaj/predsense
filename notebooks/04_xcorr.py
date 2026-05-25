"""Phase 6: Lagged cross-correlation and deeper analysis."""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

FIGS = Path("outputs/figures")
TABS = Path("outputs/tables")

df = pd.read_parquet("data/processed/uc1.parquet")
df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], utc=False)

# ── Resample to 1-minute bins for cross-correlation (raw is ~1s cadence) ──────
df_1min = df.set_index("TIMESTAMP").resample("1min").agg({
    "CW1_MAIN_RESERVOIR_PRESSURE": "mean",
    "CW1_COMPRESSOR_RUNNING": "mean",
    "CW2_COMPRESSOR_RUNNING": "mean",
    "TRAIN_SPEED_ACTUAL": "mean",
    "TRAIN_FAILURE_TYPE": "last",
}).dropna()

# Pressure derivative (bar/min)
df_1min["dP_dt"] = df_1min["CW1_MAIN_RESERVOIR_PRESSURE"].diff()

# ── Split early / late ────────────────────────────────────────────────────────
split_ts = pd.Timestamp("2025-02-21 00:00:00", tz="Europe/Vienna")
early = df_1min[df_1min.index < split_ts].dropna()
late  = df_1min[df_1min.index >= split_ts].dropna()

MAX_LAG_MIN = 30  # lags from -30 to +30 minutes

def lagged_xcorr(x, y, max_lag):
    """Pearson correlation of x with y shifted by lag (minutes)."""
    lags = range(-max_lag, max_lag + 1)
    corrs = []
    n = len(x)
    for lag in lags:
        if lag >= 0:
            xi = x.iloc[:n-lag].values if lag > 0 else x.values
            yi = y.iloc[lag:].values   if lag > 0 else y.values
        else:
            xi = x.iloc[-lag:].values
            yi = y.iloc[:n+lag].values
        if len(xi) < 10:
            corrs.append(np.nan)
            continue
        corrs.append(np.corrcoef(xi, yi)[0, 1])
    return list(lags), corrs

# CW1: dP/dt vs CW1_COMPRESSOR_RUNNING
lags_e, xc_e_cw1 = lagged_xcorr(early["dP_dt"], early["CW1_COMPRESSOR_RUNNING"], MAX_LAG_MIN)
lags_l, xc_l_cw1 = lagged_xcorr(late["dP_dt"],  late["CW1_COMPRESSOR_RUNNING"],  MAX_LAG_MIN)

# CW2: no pressure variable — use CW2_COMPRESSOR_RUNNING vs speed as control
lags_e2, xc_e_cw2 = lagged_xcorr(early["CW2_COMPRESSOR_RUNNING"], early["TRAIN_SPEED_ACTUAL"], MAX_LAG_MIN)
lags_l2, xc_l_cw2 = lagged_xcorr(late["CW2_COMPRESSOR_RUNNING"],  late["TRAIN_SPEED_ACTUAL"],  MAX_LAG_MIN)

# Save tables
xcorr_df = pd.DataFrame({
    "lag_min": lags_e,
    "early_CW1_dP_vs_comp": xc_e_cw1,
    "late_CW1_dP_vs_comp": xc_l_cw1,
    "early_CW2_comp_vs_speed": xc_e_cw2,
    "late_CW2_comp_vs_speed": xc_l_cw2,
})
xcorr_df.to_csv(TABS / "lagged_xcorr.csv", index=False)

# ── Figure 07 ─────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 1, figsize=(12, 8))

axes[0].plot(lags_e, xc_e_cw1, label="Early (Feb 17-20)", color="#2ecc71", lw=1.5)
axes[0].plot(lags_l, xc_l_cw1, label="Late (Feb 21-24)",  color="#e74c3c", lw=1.5)
axes[0].axhline(0, color="black", lw=0.5)
axes[0].axvline(0, color="gray", lw=0.5, linestyle="--")
axes[0].set_ylabel("Pearson r")
axes[0].set_title("CW1: Lagged cross-correlation — dP/dt vs CW1_COMPRESSOR_RUNNING")
axes[0].legend()
axes[0].set_xlabel("Lag (minutes, positive = compressor leads pressure derivative)")

axes[1].plot(lags_e2, xc_e_cw2, label="Early (Feb 17-20)", color="#2ecc71", lw=1.5)
axes[1].plot(lags_l2, xc_l_cw2, label="Late (Feb 21-24)",  color="#e74c3c", lw=1.5)
axes[1].axhline(0, color="black", lw=0.5)
axes[1].axvline(0, color="gray", lw=0.5, linestyle="--")
axes[1].set_ylabel("Pearson r")
axes[1].set_title("CW2 control: Lagged cross-correlation — CW2_COMPRESSOR_RUNNING vs TRAIN_SPEED")
axes[1].legend()
axes[1].set_xlabel("Lag (minutes)")

fig.tight_layout()
fig.savefig(FIGS / "07_lagged_xcorr.png", dpi=150)
plt.close()

# ── Report peak correlations ───────────────────────────────────────────────────
print("=== CW1 dP/dt vs CW1_COMPRESSOR_RUNNING ===")
for period, corrs, lags in [
    ("Early", xc_e_cw1, lags_e),
    ("Late",  xc_l_cw1, lags_l),
]:
    arr = np.array(corrs)
    idx_peak = np.nanargmax(np.abs(arr))
    print(f"  {period}: peak r={arr[idx_peak]:.3f} at lag={lags[idx_peak]} min")

print("\n=== CW2 COMPRESSOR vs SPEED (control) ===")
for period, corrs, lags in [
    ("Early", xc_e_cw2, lags_e2),
    ("Late",  xc_l_cw2, lags_l2),
]:
    arr = np.array(corrs)
    idx_peak = np.nanargmax(np.abs(arr))
    print(f"  {period}: peak r={arr[idx_peak]:.3f} at lag={lags[idx_peak]} min")

# ── Granger causality: hourly CW1 duty-cycle and pressure ─────────────────────
try:
    from statsmodels.tsa.stattools import grangercausalitytests
    hourly = pd.read_csv(TABS / "hourly_aggregates.csv", parse_dates=["hour_bin"])
    # Use only normal-operation rows (no failure)
    h_normal = hourly[hourly["failure_type"] == "No Failure"][["cw1_comp_duty", "cw1_pressure_mean"]].dropna()
    if len(h_normal) > 20:
        print("\n=== Granger causality: CW1 duty-cycle -> CW1 pressure (normal hours) ===")
        gc_results = grangercausalitytests(h_normal[["cw1_pressure_mean", "cw1_comp_duty"]], maxlag=4, verbose=False)
        for lag, res in gc_results.items():
            pval = res[0]["ssr_ftest"][1]
            print(f"  lag {lag}: p={pval:.4f}")
except Exception as e:
    print(f"Granger test skipped: {e}")

print("\nPhase 6 complete.")
