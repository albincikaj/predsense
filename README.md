# references/ — Access protocol

> **For Claude Code:** Read this file in full before touching any other
> file under `references/`. The rules here are binding.

This directory holds peer work that may inform our methodology without
biasing our analytical judgement. Two tiers, two access rules.

---

## `methodology/` — open anytime

Redacted material describing *how* colleagues approached the labelling
work. No substantive conclusions, no named variables, no time windows.

Acceptable contents:
- Label taxonomy and naming conventions used in Predsense.
- Export and import file formats, column layouts.
- Plot styling and figure structure templates.
- General Predsense usage notes and shortcuts.
- Report skeleton or table of contents (headings only).

Before adding any file here, the user must redact:
- Identification of CW1 vs CW2 as the failing wagon.
- Names of any "smoking gun" or early-warning variables.
- Specific labelled time windows, changepoint timestamps, thresholds.
- Interpretive narrative.

---

## `sealed/` — gated until Phase 5.5 of PROGRESS.md

Unredacted colleague work. Conclusions intact.

**Claude Code:** Do not list, view, open, grep, or otherwise inspect any
file in `sealed/` before Phase 5.5 of `PROGRESS.md` is reached. Phase 5.5
requires that:
1. The Phase 3 hypothesis is written into the Decision Log and committed
   to git (commit message containing "Phase 3 hypothesis sealed").
2. The Phase 5 reconciliation results are written into the Decision Log
   and committed to git (commit message containing "Phase 5 reconciliation
   sealed").

If you are about to read this folder and you cannot point to both commit
hashes, stop. Tell the user instead, and resume only after the
prerequisites are met.

Once the gate opens, follow the Phase 5.5 protocol from `PROGRESS.md`
section 5:
- Snapshot the Phase 3 and Phase 5 Decision Log entries.
- Produce `outputs/tables/reference_crosscheck.csv`.
- Log any finding revision as a new entry titled "Revision after Tier 2
  review". Never edit earlier entries.
- Disclose in the report's Methodology section that the reference was
  consulted in Phase 5.5.

---

## Relaxation for different use cases

If the colleague example is from a *different* failure scenario (leveling
system on motor wagons, pasteurization, etc.) rather than the same
compressor scenario on control wagons, the contamination risk on
conclusions is low. The user may move the material into `methodology/`
after light redaction of any shared analytical framings. The labelling
methodology itself transfers across use cases and is the main value of
the reference. Note this decision in the Decision Log when made.
