---
name: pbpk-apriori
description: >
  Answer questions about, run, and reproduce the PBPK mAb NAM tutorial repository.
  Covers the a priori workflow (Stages 1–5, Docker commands), the pre-computed study
  design results (Stages 6–8, CSV tables for Golimumab and Nivolumab at 0.1–30 mg/kg),
  fold-error interpretation, and routing between the two objectives of the repository.
  Use when asked to run simulations, check accuracy, answer study-design questions
  (group size, dose, animal count), or explain any part of this repository.
---

# PBPK mAb NAM Tutorial — skill

## What this repository contains

This repository has **two separate objectives**, each with its own folder and stage numbering.

**Objective 1 — A priori PBPK predictions** (`02_APriori_PBPK_Workflow/`)
Can a PBPK model predict monkey and human antibody PK from lab measurements alone,
before any in vivo data? Tested on 8 approved mAbs across 5 targets.

| Stage | Script | What it does |
|---|---|---|
| 1 | `01_Setup_Configurations.qmd` | Build simulation configuration workbooks |
| 2 | `02_Run_Sims.qmd` | Run all monkey and human dose scenarios |
| 3 | `03_Process_Sims_Outputs.qmd` | Evaluate predictions; produce fold-error report |
| 4 (optional) | `04_LocalSensitivityAnalysis.qmd` | One-way sensitivity of clearance to 3 parameters |
| 5 (optional) | `05_Supplementary_Fold_Error_Tornado_Plot.qmd` | Generate the tornado figure and source table |

The Docker `apriori` command runs Stages 1, 2, 3, and 5 in sequence.
Stage 4 runs separately via the `sensitivity` command.
**Stages 6, 7, and 8 are not available as Docker commands.**

**Objective 2 — Study design reanalysis** (`03_Study_Simulations/`)
If a monkey study is still needed, how small can it be? Simulated 100,000 profiles
across group sizes, dose levels, and variability scenarios. Results are pre-computed.

| Stage | Script | What it does |
|---|---|---|
| 6 | `Step1_Prepare_Study_Design_Inputs.qmd` | Build uncertainty draws and population inputs |
| 7 | `Step2_Run_Study_Design_Simulations.qmd` | Run 100k profiles (hours; checkpointed) |
| 8 | `Step3_Postprocess_Study_Design_Results.qmd` | Calculate endpoints and design success rates |

**Stages 6–8 do not need to be re-run.** All results are committed to the repository and
can be read directly from the CSV tables listed in the Study Design section below.

---

## Rules (from the repository README "Appropriate uses of an LLM")

- Never invent, estimate, or change biological parameters, doses, or observed data.
- Never edit files under `00_Data/`, `01_Models/`, or the `.qmd` scripts unless the user
  explicitly requests that specific change.
- Never choose or change model structure.
- Report a run as successful only if the runner prints `MATCH` (for `apriori`) or
  finishes without `STOPPED` (other commands). Otherwise quote the `STOPPED` line and
  the log file path it names.
- Do not send confidential or proprietary molecule information to any service the user
  has not approved.

---

## Prerequisites

- Repository cloned with `git clone` (not downloaded as a ZIP). The `apriori` and
  `compare` commands use `git` history to verify fold errors; a ZIP download has no
  history and the comparison will fail silently.
- Branch must be `main` (v0.2.1 or later). Running on `corrections_v0.2.0` produces
  `STOPPED: This checkout still has the v0.2.0 file-name bug`.
- Docker Desktop installed and running ("Engine running" in the system tray).

---

## Running the a priori workflow (Stages 1–5)

### Commands

| Command | Description | Time |
|---|---|---|
| `apriori` | Stages 1, 2, 3, 5 in sequence; stops at the first failure; refuses to reuse an old simulation run; compares the fold-error table against the committed published table | ~6 min |
| `summary` | Within-2-fold counts by species and endpoint from the current table | seconds |
| `compare` | Comparison with the committed table only; does not re-run simulations | seconds |
| `sensitivity` | Stage 4 — one-way local sensitivity analysis | ~15 min |
| `versions` | R, Quarto, rSharp, ospsuite, esqlabsR, .NET versions inside the image | seconds |
| `build` | Rebuild the image explicitly | 15–30 min |
| `help` | List all commands | seconds |

### How to run — by platform

**Windows (PowerShell or Command Prompt):**
```
powershell -ExecutionPolicy Bypass -File docker\pbpk.ps1 <command>
```

**macOS or Linux:**
```
bash docker/pbpk.sh <command>
```

**Docker Compose (any platform):**
```
docker compose run --rm pbpk <command>
```

**Direct Docker — use this if the launchers are blocked by your environment:**
```
docker run --rm --platform linux/amd64 -v "${PWD}:/work" pbpk-mab-nam <command>
```
On macOS/Linux replace `${PWD}` with `$PWD`. On Windows Command Prompt use `%cd%`.

Note: the `build` command is handled by the launchers, not the container. To rebuild
without a launcher, run the Docker build command directly:
```
docker build --platform linux/amd64 -t pbpk-mab-nam docker
```

### First run

The first run builds the Docker image automatically (~1 GB download, 15–30 minutes).
The line `==> Building the 'pbpk-mab-nam' image` is expected output — do not interrupt.
Apple Silicon Macs (M1/M2/M3/M4) run the image via Rosetta 2; the launchers pass
`--platform linux/amd64` automatically. Results are identical to Intel hardware.
Subsequent runs start in seconds.

### Workflow

1. Run `versions` to confirm the environment is correct.
2. Run `apriori`. Do not interrupt. Expected duration ~6 minutes.
3. If it prints `MATCH` — run `summary` and report the accuracy table.
4. If it prints `DIFFERENT` or `STOPPED` — quote the exact output and the log path
   under `_pbpk_logs/`. Do not attempt to fix scientific inputs.
5. Outputs after a successful `apriori` run:
   - Main report: `02_APriori_PBPK_Workflow/Scripts/03_Process_Sims_Outputs.html`
   - Fold-error table: `02_APriori_PBPK_Workflow/SimsOutputs/Tables/Supplement_Fold_Error_Tornado_Data.csv`
   - New simulation folder: path recorded in `02_APriori_PBPK_Workflow/SimsOutputs/latest_simulation_run.txt`
6. After `sensitivity` (Stage 4): report is at `02_APriori_PBPK_Workflow/Scripts/04_LocalSensitivityAnalysis.html`
7. The run modifies tracked files (configuration workbooks, HTML reports, tornado figure).
   To restore: `git checkout -- .` and delete the new timestamped folder under
   `02_APriori_PBPK_Workflow/SimsOutputs/SimulationResults/`.

### Interpreting fold errors

- Fold error = predicted / observed. Within 0.5–2.0 = within 2-fold.
- Clearance is evaluated only when the observed data allow a reliable terminal phase
  (extrapolated AUC fraction ≤ 20%), so fewer clearance rows are evaluated than AUC or Cmax.
- All predictions are a priori: observed data are used only for evaluation, never for fitting.
- 8 antibodies, 5 targets: Tocilizumab (IL-6R), Nivolumab and Pembrolizumab (PD-1),
  Atezolizumab and Avelumab (PD-L1), Adalimumab and Golimumab (TNF-alpha), Bevacizumab (VEGF-A).

---

## Study design questions (Stages 6–8) — pre-computed results

**Do not attempt to re-run Stages 6, 7, or 8.** Stage 7 takes several hours and is not
available as a Docker command. All results are already committed to the repository.

### What is covered

- Molecules: **Golimumab** and **Nivolumab**
- Doses: **0.1, 1, 3, 10, 30 mg/kg**
- Designs: **2, 3, or 5 dose groups**
- Animals per group: **2, 3, or 6**
- Variability scenarios: **30% CV** and **60% CV** for 5 shared mechanistic inputs
- Endpoints: AUC0-28d, Cmax, Terminal clearance
- 100 replicates per molecule and variability scenario

### Where the results are

| Question | File |
|---|---|
| Does this design work overall? | `03_Study_Simulations/SimsOutputs/Step3_Results/Tables/study_design_overall_success.csv` |
| Performance by endpoint (AUC, Cmax, clearance)? | `03_Study_Simulations/SimsOutputs/Step3_Results/Tables/study_design_endpoint_success.csv` |
| Fold errors by dose? | `03_Study_Simulations/SimsOutputs/Step3_Results/Tables/study_design_fold_error_summary.csv` |
| Replicate-level fold errors? | `03_Study_Simulations/SimsOutputs/Step3_Results/Tables/study_design_replicate_matched_fold_error.csv` |
| Replicate vs dense truth comparison? | `03_Study_Simulations/SimsOutputs/Step3_Results/Tables/study_design_replicate_matched_dense_truth.csv` |
| Nominal/typical reference fold errors? | `03_Study_Simulations/SimsOutputs/Step3_Results/Tables/study_design_nominal_typical_fold_error_summary.csv` |
| QC and analysis diagnostics? | `03_Study_Simulations/SimsOutputs/Step3_Results/Tables/study_design_analysis_qc.csv` |

### How to answer a study design question

1. Read the relevant CSV directly — do not run any simulation.
2. Filter by the molecule, dose, design, and N_per_group the user asked about.
3. Report `Fraction_within_2fold` from `study_design_overall_success.csv` for the overall result.
4. If the user asks by endpoint, use `study_design_endpoint_success.csv`.
5. If the user asks about fold errors at a specific dose, use `study_design_fold_error_summary.csv`.
6. Always state that results are conditional on the Golimumab and Nivolumab truth models,
   the configured variability and population assumptions, and the 0.5–2-fold criterion as a
   tutorial threshold — not a universal design standard.

### Example: "What happens at 0.1 mg/kg with 2 monkeys per group?"

Read `study_design_fold_error_summary.csv`, filter Dose_mg_kg = 0.1, N_per_group = 2,
report Fraction_within_2fold for each molecule, endpoint, and variability scenario.
Then check `study_design_overall_success.csv` for the overall design success rate.

---

## What this skill does not cover

- **Adding a new antibody or target.** See the repository README section "Applying the
  workflow to another mAb". This requires new PKML model files and parameter workbook
  entries; it cannot be done through Docker commands alone.
- **Editing model structure.** PK-Sim and MoBi are required; they are not included in
  the Docker image.
- **Study design for molecules other than Golimumab and Nivolumab.** The pre-computed
  tables cover only these two molecules as configured in Stage 6.
