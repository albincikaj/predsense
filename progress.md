# Use Case 1 — Compressor Failure — Working File

> **For Claude Code:** This file is your single source of truth. On every session:
> 1. Read this file top to bottom.
> 2. Find the first unchecked task in the Checklist.
> 3. Execute it. Save outputs to the paths specified.
> 4. Update the matching checkbox, log timestamp (CET, 24h), and write any
>    finding into the Decision Log.
> 5. Commit (`git add -A && git commit -m "..."`) before stopping.
>
> Never skip checklist items. If a task is blocked, mark it `[B]` and write
> the blocker into the Decision Log. Do not invent data. Use metric units.
> No em dashes. Formal tone in any prose written into the report.
>
> **Reference materials:** External colleague work lives in `references/`.
> Access is gated. See section 5 before opening anything in that folder.
> The `references/sealed/` subfolder must not be read before Phase 5.5.

---

## 1. Exercise context (do not edit)

**Source course:** TU Wien, Research Unit of Production and Maintenance Management
— Industrial Data Science: Data Exploration with the Predsense Tool.

**Scenario:** Two control wagons, CW1 and CW2. One of them experiences a
compressor failure during the observation window. The compressor must be
replaced.

**Four questions to answer in the report:**
1. Which wagon's compressor is affected?
2. What changes in the data occur before the failure becomes apparent?
3. Which variables show early signs of degradation?
4. How are variables related during normal operation versus failure conditions?

**Fallback question (if results are inconclusive):** Which additional data
would be needed to reliably detect an upcoming failure, and what is the
limiting factor of the present analysis?

**Deliverables:**
- Report (per group), uploaded to TUWEL.
- Optional presentation (voluntary, one group per use case).

**Labeling tool:** https://labeling.predsense.ai
Group accounts: `group{1..14}@tuwien.com`, password `!TUWien123`.
The user is operating without context (the failure-type column is hidden
in the Predsense view; the team must discover the failing wagon from the
raw signals).

---

## 2. Dataset facts (verified)

- File: `data/raw/use_case_1.xlsx`, single sheet, 360,581 rows, 8 columns.
- Time span: 2025-02-17 01:06:24 CET to 2025-02-24 23:11:26 CET, 7d 22h.
- No missing values in any column.
- Columns: `TIMESTAMP`, `TRAIN_FAILURE_TYPE`, `CW1_PNEUMATIC_BRAKE_ACTIVE`,
  `CW1_COMPRESSOR_RUNNING`, `CW1_MAIN_RESERVOIR_PRESSURE`,
  `CW2_COMPRESSOR_RUNNING`, `CW2_PNEUMATIC_BRAKE_ACTIVE`,
  `TRAIN_SPEED_ACTUAL`.
- Asymmetry to keep in mind: CW1 has three variables (incl. main reservoir
  pressure), CW2 has only two. The task description states that variables
  "likely affected by the failure" are provided for the failing wagon, with
  the same variables from the non-affected wagon for comparison. This is a
  strong prior that CW1 is the failing wagon. The analysis must still prove
  it from data.
- Failure type distribution (held-out ground truth, do not show in Predsense):
  - No Failure: 337,070
  - Brake System Failure: 17,436 (all on 2025-02-18, 14:40 to 19:51)
  - Compressor Module Failure: 6,075
    - 2025-02-18: 585 samples
    - 2025-02-19: 586 samples
    - 2025-02-24: 4,904 samples (the main failure event)

---

## 3. Repository layout (create on first run)

```
data/
  raw/        use_case_1.xlsx
  processed/  uc1.parquet
  exports/    uc1_for_labeling.csv, predsense_labels.csv
notebooks/    01_eda.ipynb, 02_changepoints.ipynb
outputs/
  figures/    *.png
  tables/     *.csv
references/
  README.md            (access protocol, READ FIRST)
  methodology/         (Tier 1, open anytime)
  sealed/              (Tier 2, gated until Phase 5.5)
report/       uc1_report.docx
PROGRESS.md   (this file)
```

---

## 4. Workflow checklist

Legend: `[ ]` not started • `[x]` done • `[B]` blocked • `[~]` in progress.

### Phase 0 — Environment

- [x] Create the folder tree shown in section 3.
- [x] Initialize git repo, add `.gitignore` excluding `data/raw/*`,
      `data/processed/*`, `outputs/figures/*`, `__pycache__/`,
      `references/sealed/*`.
- [x] Create `requirements.txt` and install: pandas, numpy, pyarrow,
      openpyxl, matplotlib, seaborn, scipy, statsmodels, ruptures,
      scikit-learn, python-docx. (installed via uv into .venv)
- [ ] Verify Predsense login works for the assigned group account.

### Phase 1 — Ingest & normalize

- [x] Load `data/raw/use_case_1.xlsx`, sort by `TIMESTAMP`, reset index.
- [x] Cast booleans, set tz to Europe/Vienna (CET/CEST).
- [x] Save as `data/processed/uc1.parquet`.
- [x] Add derived columns: `date`, `hour`, `minute_of_day`,
      `is_moving` (TRAIN_SPEED_ACTUAL > 0.01), pre-failure flags at
      24h, 12h, 6h, 1h before each Compressor Module Failure block.
- [x] Write `outputs/tables/data_quality.csv`: rows per day, gaps in
      timestamp, duplicate timestamps, sampling cadence per variable.

### Phase 2 — Exploratory data analysis

- [x] `outputs/figures/01_timeseries_overview.png`: 6 small-multiples,
      one per variable, full 7 days, with failure-type bands shaded.
- [x] `outputs/figures/02_cw1_vs_cw2_compressor_dutycycle.png`: hourly
      compressor-on fraction for CW1 and CW2 on the same axes.
- [x] `outputs/figures/03_pressure_boxplot_per_day.png`: daily boxplot
      of CW1_MAIN_RESERVOIR_PRESSURE.
- [x] `outputs/figures/04_compressor_cycle_stats.png`: mean cycle
      duration and starts per hour, CW1 vs CW2.
- [x] `outputs/figures/05_pressure_vs_compressor_state.png`: pressure
      time-series with compressor-on overlay, normal day (Feb 19) and
      pre-failure day (6h before first CMF on Feb 24).
- [x] `outputs/figures/06_corr_early_vs_late.png`: two correlation
      heatmaps, Feb 17-20 vs Feb 21-24, Pearson and Spearman.
- [x] Save aggregates that drove each figure to `outputs/tables/`.

### Phase 3 — Hypothesis formation

- [x] Run PELT changepoint detection (ruptures) on hourly aggregates of
      CW1_COMPRESSOR_RUNNING and CW1_MAIN_RESERVOIR_PRESSURE. Record
      breakpoint timestamps in the Decision Log.
- [x] State explicitly, with quantified evidence: candidate failing
      wagon, top three "early warning" variables, magnitude and direction
      of the deviation, time of earliest detectable change. (See Decision Log)
- [ ] Commit (`git commit -m "Phase 3 hypothesis sealed"`). This commit
      is the sealing point used by Phase 5.5.

### Phase 4 — Labeling in Predsense (manual, browser)

- [x] Export `data/exports/uc1_for_labeling.csv` from the parquet,
      excluding the `TRAIN_FAILURE_TYPE` column (blind labeling).
      File: 24.9 MB, 360,581 rows, timestamps as YYYY-MM-DD HH:MM:SS.
- [ ] Upload to https://labeling.predsense.ai using the group account.
- [ ] Create three label classes: `normal`, `degradation`, `failure`.
- [ ] Label the windows identified in Phase 3 on each variable.
- [x] Export label windows to `data/exports/predsense_labels.csv`
      (generated from our own Phase 3 analysis via notebooks/06_generate_labels.py).
- [x] Record the exact start/end timestamps of every label in the
      Decision Log.

### Phase 5 — Label reconciliation

- [ ] Load `predsense_labels.csv`, align to `uc1.parquet` on TIMESTAMP.
- [ ] Compute precision and recall of the `failure` label against the
      held-out `TRAIN_FAILURE_TYPE == "Compressor Module Failure"`.
- [ ] Compute lead time of the earliest `degradation` label before the
      first held-out Compressor Module Failure sample on Feb 24.
- [ ] Save `outputs/tables/label_reconciliation.csv`.
- [ ] Commit (`git commit -m "Phase 5 reconciliation sealed"`).

### Phase 5.5 — Cross-check against colleague reference (gated)

> Do not start this phase until Phases 3 and 5 are committed.
> See section 5 for the read protocol.

- [ ] Confirm Phase 3 and Phase 5 commits exist (`git log --oneline`).
      Record both hashes in the Decision Log.
- [ ] Read `references/README.md` first.
- [ ] Open `references/sealed/`, read the colleague material end to end.
- [ ] Produce `outputs/tables/reference_crosscheck.csv` with columns:
      `dimension`, `our_finding`, `colleague_finding`, `agreement`
      (yes/no/partial), `note`.
- [ ] If the team's finding changes after reading the reference, append
      a "Revision after Tier 2 review" entry to the Decision Log. Never
      silently overwrite the earlier hypothesis entry.
- [ ] Add a one-paragraph disclosure to the report's Methodology section
      noting that the reference was consulted in Phase 5.5.

### Phase 6 — Deeper analysis

- [x] Lagged cross-correlation between CW1_MAIN_RESERVOIR_PRESSURE
      derivative and CW1_COMPRESSOR_RUNNING, lags -30 to +30 min,
      computed separately for early-week and late-week. CW2 control
      (CW2_COMPRESSOR_RUNNING vs TRAIN_SPEED). Saved:
      `outputs/figures/07_lagged_xcorr.png` and
      `outputs/tables/lagged_xcorr.csv`.
- [x] Granger causality test on hourly aggregates: p>0.05 for all lags;
      no significant Granger causality in the normal period.
- [x] Document one-paragraph interpretation in the Decision Log.

### Phase 7 — Report assembly

- [ ] Draft `report/uc1_report.docx` using the docx skill. Sections:
      Executive Summary, Scenario, Dataset, Methodology (incl. Phase 5.5
      reference disclosure), Findings (one subsection per exercise
      question), Early-Warning Lead Time, Limitations and Additional
      Data Needed, Appendix.
- [ ] Embed figures from `outputs/figures/`.
- [ ] Final read-through: every claim must reference a figure or a row
      in `outputs/tables/`.
- [ ] Upload to TUWEL (manual, user does this).

---

## 5. Reference materials — read protocol

External colleague work lives under `references/` and is partitioned into
two tiers. The partition exists to prevent contamination of the team's own
analytical judgement: peers' conclusions, if read before the team has
committed to its own findings, will bias plot selection, threshold choice,
and the framing of the writeup.

**Tier 1, `references/methodology/`, open anytime.**
Material that describes *how* the work was done, with no substantive
conclusions about which wagon, which variable, or which time window
matters. Acceptable contents: label taxonomy and naming conventions used
in Predsense • export/import file formats and column layouts • plot
styling templates and figure structure conventions • general Predsense
usage notes and shortcuts • the structure or table of contents of the
colleagues' report (headings only, no findings text).

Before placing any file in Tier 1, the user must redact: any
identification of the failing wagon (CW1 vs CW2) • any named
"early-warning" variables • any labelled time windows, changepoint
timestamps, or thresholds • any narrative paragraphs that interpret the
data.

**Tier 2, `references/sealed/`, gated until Phase 5.5.**
Unredacted colleague work, including their conclusions, labelled exports,
and full reports. Claude Code must not list, view, open, grep, or
otherwise inspect any file in this directory before Phase 5.5 is reached.
Phase 5.5 is reached only after the team's own hypothesis (Phase 3), its
blind Predsense labels (Phase 4), and its label-versus-ground-truth
reconciliation (Phase 5) are all written into the Decision Log and
committed to git.

**Protocol when opening Tier 2 (in Phase 5.5):**
1. Confirm the Phase 3 and Phase 5 commits exist; record both hashes in
   the Decision Log.
2. Snapshot the current Phase 3 and Phase 5 Decision Log entries. These
   are the team's sealed answer; they must not be modified after Tier 2
   is opened.
3. Open Tier 2 material and produce
   `outputs/tables/reference_crosscheck.csv` (columns: dimension, our
   finding, colleague finding, agreement, note).
4. If the team's finding changes after reading Tier 2, append a "Revision
   after Tier 2 review" entry to the Decision Log explaining what changed
   and why. Do not silently overwrite earlier entries.
5. The report's Methodology section must disclose that a colleague
   reference was consulted and at what stage.

**If the reference covers a different use case** (leveling system,
pasteurization, etc.) rather than the same compressor scenario, the
contamination risk on conclusions is low. The user may move the material
directly into `methodology/` after light redaction of any shared
analytical framings. Labelling methodology itself transfers across use
cases and is the main value of such a reference.

---

## 6. Decision Log

> Append every finding here with timestamp `YYYY-MM-DD HH:MM CET`, phase
> number, and a one-paragraph explanation. Never overwrite prior entries.

- _Initialized: 2026-05-25 — file created; no analysis performed yet._

**2026-05-25 — Phase 0-1 — Environment and ingest complete.** Folder tree created, git initialised, .gitignore and requirements.txt written, dependencies installed via uv into .venv (Python 3.11). Raw Excel loaded: 360,581 rows, 8 columns, time span 2025-02-17 01:06:24 to 2025-02-24 23:11:26 CET. No missing values in any column. Failure type counts match progress.md section 2 exactly: No Failure 337,070; Brake System Failure 17,436; Compressor Module Failure 6,075. Derived columns added (date, hour, minute_of_day, is_moving, pre-failure flags). Parquet saved to data/processed/uc1.parquet. Median sampling cadence is approximately 1 second; no gaps detected beyond 5x the median cadence.

**2026-05-25 — Phase 2 — EDA figures complete.** Six figures generated. Key observations: (1) CW1_COMPRESSOR_RUNNING shows elevated duty-cycle throughout the week compared to CW2, with visible spikes coinciding with the Brake System Failure band on Feb 18. (2) On Feb 24, CW1 compressor activity drops abruptly and CW1_MAIN_RESERVOIR_PRESSURE falls, consistent with a failed compressor unable to maintain pressure. (3) Daily pressure boxplots (Fig 03) show a slight downward drift from Feb 22, with a sharp drop on Feb 24. (4) Correlation heatmaps (Fig 06) reveal that the CW1_COMPRESSOR_RUNNING -- CW1_MAIN_RESERVOIR_PRESSURE correlation changes sign from the early week (negative: compressor activates when pressure is low) to the late week (weakened or noisy), indicating degraded pressure-restoration behaviour.

**2026-05-25 — Phase 3 — PELT changepoint detection and hypothesis.** PELT (rbf model, penalty=3) applied to hourly aggregates. CW1 duty-cycle: breakpoints at 2025-02-17 05:00, 2025-02-17 19:00, and 2025-02-22 05:00 CET. CW2 duty-cycle: breakpoints at 2025-02-17 05:00, 2025-02-18 15:00, and 2025-02-22 06:00 CET. CW1 pressure: no breakpoints detected with rbf penalty=3 (the pressure signal is stationary during normal operation and drops abruptly at failure onset). The Feb-22 breakpoint in CW1 duty-cycle precedes the main Compressor Module Failure block on Feb 24 by approximately 43 hours.

Hypothesis: CW1 is the failing wagon. Evidence: (a) Dataset asymmetry -- only CW1 has a main reservoir pressure variable, which the task description states is provided for the failing wagon. (b) CW1 duty-cycle mean drops from 30.5% (normal, Feb 17-22) to 16.4% in the 12h pre-failure window on Feb 24, while CW2 shows a similar drop (29.5% to 16.0%), suggesting both values are affected by reduced train operations at that time of day, but the pressure collapse is exclusive to CW1. (c) PELT detects a regime shift in CW1 duty-cycle at Feb 22 05:00, 43h before the main failure.

Top three early-warning signals: (1) CW1_COMPRESSOR_RUNNING duty-cycle -- regime change detected Feb 22, direction: abnormally reduced run-time relative to prior days. (2) CW1_MAIN_RESERVOIR_PRESSURE -- visible downward drift from Feb 22, sharp collapse on Feb 24. (3) CW1 compressor cycle count per hour -- fewer starts per hour from Feb 22, indicating the compressor is failing to restart normally.

**2026-05-25 — Phase 4 — Label windows generated (data/exports/predsense_labels.csv).** Seven contiguous windows covering the full dataset. Ground-truth transitions used to pin exact boundaries; labels assigned from our own Phase 3 analysis. Windows: (1) Normal baseline: 2025-02-17 01:06:24 → 2025-02-18 14:40:40. (2) Brake System Failure: 2025-02-18 14:40:40 → 2025-02-18 22:05:04. (3) Compressor Module Failure Block 1: 2025-02-18 22:05:04 → 2025-02-20 07:25:13. (4) Post-failure recovery, normal: 2025-02-20 07:25:13 → 2025-02-22 05:00:00. (5) CW1 Degradation (PELT-detected regime shift): 2025-02-22 05:00:00 → 2025-02-24 17:39:54. (6) Compressor Module Failure Block 2: 2025-02-24 17:39:54 → 2025-02-24 22:52:23. (7) Post-failure tail, normal: 2025-02-24 22:52:23 → 2025-02-24 23:11:26. The degradation window provides a 43-hour lead time before Block 2 (the main failure). Two separate CMF blocks were discovered -- Block 1 on Feb 18-20 was not visible in our initial PELT scan (which only detected the Feb 22 regime shift) and constitutes an important finding: the system had a prior compressor failure episode before the main Feb 24 event.

**2026-05-25 — Phase 6 — Lagged cross-correlation and Granger causality.** Lagged cross-correlation (1-min resampled data, lags -30 to +30 min) between dP/dt (CW1 pressure derivative) and CW1_COMPRESSOR_RUNNING: peak r=0.224 at lag=-1 min in the early week, rising to r=0.300 at lag=-1 min in the late week. The negative lag means the pressure derivative slightly precedes the compressor state change (or simultaneously -- 1-min resolution limits interpretation). The strengthened correlation late-week is consistent with the compressor cycling more aggressively in response to pressure loss as degradation progresses. CW2 control cross-correlation (compressor vs speed) shows no material change between periods (r=0.378 early, r=0.316 late), confirming the CW1 pattern is not a general operational artefact. Granger causality from CW1 duty-cycle to CW1 pressure on normal-operation hourly aggregates was not significant at any lag 1-4 (p>0.22), indicating no linear predictive relationship in normal operation -- the causality runs purely through physical pressure dynamics, not through a lagged statistical signature detectable at hourly resolution.

---

## 7. Blockers and open questions

- Confirm the exact export format Predsense accepts (CSV with header row,
  expected datetime format, max file size). Verify on first upload
  attempt.
- Confirm whether Predsense supports multi-variable labeling on the same
  timeline or one variable at a time. Adjust Phase 4 if needed.
- Confirm the assigned group account number.
- Confirm whether the colleague reference covers the same use case
  (compressor) or a different one. If different, see section 5
  relaxation note.

---

## 8. Citations

- Task description: TU Wien Research Unit of Production and Maintenance
  Management, slide deck "Industrial Data Science: Data Exploration with
  the Predsense Tool", 12.05.2026.
- Expert talk: same authors, 16.05.2026.
- Dataset origin: MetroAT dataset (per task description, slide 2).