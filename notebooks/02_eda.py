"""Phase 2: Exploratory data analysis — all figures and aggregate tables."""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from pathlib import Path

sns.set_theme(style="whitegrid", font_scale=0.9)
FIGS = Path("outputs/figures")
TABS = Path("outputs/tables")

# ── Load ──────────────────────────────────────────────────────────────────────
df = pd.read_parquet("data/processed/uc1.parquet")
df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], utc=False)

# Failure-type colour map
FTYPE_COLORS = {
    "No Failure": "#d4e6f1",
    "Brake System Failure": "#f9e4b7",
    "Compressor Module Failure": "#f5b7b1",
}

def add_failure_bands(ax, df, alpha=0.25):
    """Shade vertical bands by failure type."""
    for ftype, color in FTYPE_COLORS.items():
        mask = df["TRAIN_FAILURE_TYPE"] == ftype
        if not mask.any():
            continue
        starts = df.loc[mask & (~mask.shift(1, fill_value=False)), "TIMESTAMP"]
        ends   = df.loc[mask & (~mask.shift(-1, fill_value=False)), "TIMESTAMP"]
        for s, e in zip(starts, ends):
            ax.axvspan(s, e, color=color, alpha=alpha, linewidth=0)


# ════════════════════════════════════════════════════════════════════════════
# Figure 01 — time-series overview, 7 small-multiples
# ════════════════════════════════════════════════════════════════════════════
print("Figure 01 …")
numeric_cols = [
    "CW1_PNEUMATIC_BRAKE_ACTIVE",
    "CW1_COMPRESSOR_RUNNING",
    "CW1_MAIN_RESERVOIR_PRESSURE",
    "CW2_COMPRESSOR_RUNNING",
    "CW2_PNEUMATIC_BRAKE_ACTIVE",
    "TRAIN_SPEED_ACTUAL",
    "TRAIN_FAILURE_TYPE",  # shown as categorical
]
plot_cols = [
    ("CW1_PNEUMATIC_BRAKE_ACTIVE",  "CW1 Brake Active"),
    ("CW1_COMPRESSOR_RUNNING",      "CW1 Compressor Running"),
    ("CW1_MAIN_RESERVOIR_PRESSURE", "CW1 Main Reservoir Pressure (bar)"),
    ("CW2_COMPRESSOR_RUNNING",      "CW2 Compressor Running"),
    ("CW2_PNEUMATIC_BRAKE_ACTIVE",  "CW2 Brake Active"),
    ("TRAIN_SPEED_ACTUAL",          "Train Speed (km/h)"),
]

fig, axes = plt.subplots(len(plot_cols), 1, figsize=(16, 14), sharex=True)
for ax, (col, label) in zip(axes, plot_cols):
    add_failure_bands(ax, df)
    if df[col].dtype == bool:
        ax.fill_between(df["TIMESTAMP"], df[col].astype(int), step="post",
                        alpha=0.7, color="#2980b9")
    else:
        ax.plot(df["TIMESTAMP"], df[col], lw=0.3, color="#2c3e50")
    ax.set_ylabel(label, fontsize=8)
    ax.tick_params(axis="x", labelsize=7)

# Legend for bands
patches = [mpatches.Patch(color=c, alpha=0.5, label=l)
           for l, c in FTYPE_COLORS.items()]
axes[0].legend(handles=patches, loc="upper right", fontsize=7, framealpha=0.8)
axes[0].set_title("Full 7-day time-series overview with failure-type bands", fontsize=10)
fig.tight_layout()
fig.savefig(FIGS / "01_timeseries_overview.png", dpi=150)
plt.close()


# ════════════════════════════════════════════════════════════════════════════
# Figure 02 — hourly compressor duty-cycle CW1 vs CW2
# ════════════════════════════════════════════════════════════════════════════
print("Figure 02 …")
df["hour_bin"] = df["TIMESTAMP"].dt.floor("h")
duty = df.groupby("hour_bin").agg(
    cw1=("CW1_COMPRESSOR_RUNNING", "mean"),
    cw2=("CW2_COMPRESSOR_RUNNING", "mean"),
).reset_index()
duty.to_csv(TABS / "duty_cycle_hourly.csv", index=False)

fig, ax = plt.subplots(figsize=(16, 4))
ax.plot(duty["hour_bin"], duty["cw1"], lw=0.8, label="CW1", color="#e74c3c")
ax.plot(duty["hour_bin"], duty["cw2"], lw=0.8, label="CW2", color="#3498db", alpha=0.8)
add_failure_bands(ax, df)
ax.set_ylabel("Compressor-on fraction (hourly)")
ax.set_title("Hourly compressor duty-cycle: CW1 vs CW2")
ax.legend()
fig.tight_layout()
fig.savefig(FIGS / "02_cw1_vs_cw2_compressor_dutycycle.png", dpi=150)
plt.close()


# ════════════════════════════════════════════════════════════════════════════
# Figure 03 — daily boxplot of CW1_MAIN_RESERVOIR_PRESSURE
# ════════════════════════════════════════════════════════════════════════════
print("Figure 03 …")
df["date_str"] = df["TIMESTAMP"].dt.strftime("%b %d")
day_order = df.drop_duplicates("date_str").sort_values("TIMESTAMP")["date_str"].tolist()

fig, ax = plt.subplots(figsize=(12, 5))
sns.boxplot(data=df, x="date_str", y="CW1_MAIN_RESERVOIR_PRESSURE",
            order=day_order, ax=ax, palette="Blues", fliersize=1)
ax.set_xlabel("Date")
ax.set_ylabel("Pressure (bar)")
ax.set_title("Daily distribution of CW1 Main Reservoir Pressure")
fig.tight_layout()
fig.savefig(FIGS / "03_pressure_boxplot_per_day.png", dpi=150)
plt.close()

# Save daily stats
daily_pressure = df.groupby("date_str")["CW1_MAIN_RESERVOIR_PRESSURE"].describe()
daily_pressure.to_csv(TABS / "daily_pressure_stats.csv")


# ════════════════════════════════════════════════════════════════════════════
# Figure 04 — compressor cycle statistics CW1 vs CW2
# ════════════════════════════════════════════════════════════════════════════
print("Figure 04 …")

def cycle_stats(series, timestamps, label):
    """Compute per-hour mean cycle duration and inter-start interval."""
    records = []
    ts_arr = timestamps.values
    v_arr = series.values.astype(int)
    starts = np.where((v_arr[1:] == 1) & (v_arr[:-1] == 0))[0] + 1
    ends   = np.where((v_arr[1:] == 0) & (v_arr[:-1] == 1))[0] + 1
    if len(starts) == 0:
        return pd.DataFrame()
    # Pair starts/ends
    pairs = []
    ei = 0
    for si in starts:
        while ei < len(ends) and ends[ei] < si:
            ei += 1
        if ei < len(ends):
            pairs.append((si, ends[ei]))
    durations = [(ts_arr[e] - ts_arr[s]).astype("timedelta64[s]").astype(float)
                 for s, e in pairs]
    inter = [(ts_arr[starts[i+1]] - ts_arr[starts[i]]).astype("timedelta64[s]").astype(float)
             for i in range(len(starts)-1)]
    hour_bins = pd.to_datetime(ts_arr[starts]).floor("h")
    df_c = pd.DataFrame({
        "hour_bin": hour_bins,
        "duration_s": durations,
        "label": label,
    })
    start_counts = df_c.groupby("hour_bin")["duration_s"].agg(["mean", "count"]).reset_index()
    start_counts.columns = ["hour_bin", "mean_duration_s", "start_count"]
    start_counts["label"] = label
    return start_counts

cs_cw1 = cycle_stats(df["CW1_COMPRESSOR_RUNNING"], df["TIMESTAMP"], "CW1")
cs_cw2 = cycle_stats(df["CW2_COMPRESSOR_RUNNING"], df["TIMESTAMP"], "CW2")
cs_all = pd.concat([cs_cw1, cs_cw2])
cs_all.to_csv(TABS / "compressor_cycle_stats.csv", index=False)

fig, axes = plt.subplots(2, 1, figsize=(16, 7), sharex=True)
for label, color in [("CW1", "#e74c3c"), ("CW2", "#3498db")]:
    sub = cs_all[cs_all["label"] == label]
    axes[0].plot(sub["hour_bin"], sub["mean_duration_s"], lw=0.8, label=label, color=color)
    axes[1].plot(sub["hour_bin"], sub["start_count"], lw=0.8, label=label, color=color)

for ax in axes:
    add_failure_bands(ax, df)
    ax.legend()
axes[0].set_ylabel("Mean cycle duration (s)")
axes[1].set_ylabel("Starts per hour")
axes[0].set_title("Compressor cycle statistics: CW1 vs CW2")
fig.tight_layout()
fig.savefig(FIGS / "04_compressor_cycle_stats.png", dpi=150)
plt.close()


# ════════════════════════════════════════════════════════════════════════════
# Figure 05 — pressure vs compressor state: normal day vs pre-failure day
# ════════════════════════════════════════════════════════════════════════════
print("Figure 05 …")
# Normal day: Feb 19 full day; pre-failure: Feb 24 starting 6h before first CMF
cmf_mask = df["TRAIN_FAILURE_TYPE"] == "Compressor Module Failure"
first_cmf_ts = df.loc[cmf_mask, "TIMESTAMP"].min()

normal_start = pd.Timestamp("2025-02-19 00:00:00", tz="Europe/Vienna")
normal_end   = pd.Timestamp("2025-02-19 23:59:59", tz="Europe/Vienna")
pre_start    = first_cmf_ts - pd.Timedelta("6h")
pre_end      = df["TIMESTAMP"].max()

def zoom_panel(ax, sub, title):
    ax.plot(sub["TIMESTAMP"], sub["CW1_MAIN_RESERVOIR_PRESSURE"],
            lw=0.5, color="#2c3e50", label="Pressure")
    ax.fill_between(sub["TIMESTAMP"],
                    sub["CW1_COMPRESSOR_RUNNING"].astype(int) * sub["CW1_MAIN_RESERVOIR_PRESSURE"].max(),
                    step="post", alpha=0.2, color="#e74c3c", label="CW1 Compressor On")
    add_failure_bands(ax, sub, alpha=0.3)
    ax.set_title(title, fontsize=9)
    ax.set_ylabel("Pressure (bar)")
    ax.legend(fontsize=7)

normal_sub = df[(df["TIMESTAMP"] >= normal_start) & (df["TIMESTAMP"] <= normal_end)]
pre_sub    = df[(df["TIMESTAMP"] >= pre_start) & (df["TIMESTAMP"] <= pre_end)]

fig, axes = plt.subplots(2, 1, figsize=(14, 8))
zoom_panel(axes[0], normal_sub, "Normal operation: Feb 19")
zoom_panel(axes[1], pre_sub, f"Pre-failure and failure: from 6h before first CMF ({pre_start.strftime('%b %d %H:%M')})")
fig.tight_layout()
fig.savefig(FIGS / "05_pressure_vs_compressor_state.png", dpi=150)
plt.close()


# ════════════════════════════════════════════════════════════════════════════
# Figure 06 — correlation heatmaps: early week vs late week
# ════════════════════════════════════════════════════════════════════════════
print("Figure 06 …")
split_ts = pd.Timestamp("2025-02-21 00:00:00", tz="Europe/Vienna")
early = df[df["TIMESTAMP"] < split_ts].copy()
late  = df[df["TIMESTAMP"] >= split_ts].copy()

corr_cols = [
    "CW1_PNEUMATIC_BRAKE_ACTIVE",
    "CW1_COMPRESSOR_RUNNING",
    "CW1_MAIN_RESERVOIR_PRESSURE",
    "CW2_COMPRESSOR_RUNNING",
    "CW2_PNEUMATIC_BRAKE_ACTIVE",
    "TRAIN_SPEED_ACTUAL",
]

def to_numeric_df(sub):
    return sub[corr_cols].apply(lambda c: c.astype(float))

fig, axes = plt.subplots(2, 2, figsize=(14, 11))
for row_idx, (method, mname) in enumerate([("pearson", "Pearson"), ("spearman", "Spearman")]):
    for col_idx, (sub, period) in enumerate([(early, "Feb 17-20 (early)"), (late, "Feb 21-24 (late)")]):
        corr = to_numeric_df(sub).corr(method=method)
        ax = axes[row_idx][col_idx]
        sns.heatmap(corr, ax=ax, annot=True, fmt=".2f", cmap="RdBu_r",
                    vmin=-1, vmax=1, square=True, linewidths=0.5, annot_kws={"size": 7})
        ax.set_title(f"{mname} — {period}", fontsize=9)
        ax.tick_params(axis="x", rotation=45, labelsize=7)
        ax.tick_params(axis="y", rotation=0, labelsize=7)

fig.suptitle("Correlation matrices: early week vs late week", fontsize=11)
fig.tight_layout()
fig.savefig(FIGS / "06_corr_early_vs_late.png", dpi=150)
plt.close()

# Save correlation tables
for method in ["pearson", "spearman"]:
    to_numeric_df(early).corr(method=method).to_csv(TABS / f"corr_early_{method}.csv")
    to_numeric_df(late).corr(method=method).to_csv(TABS / f"corr_late_{method}.csv")

print("Phase 2 complete.")
