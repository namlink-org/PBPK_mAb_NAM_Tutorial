---
name: pbpk-apriori
description: >
  Answer questions about, run, troubleshoot, and adapt the PBPK mAb NAM tutorial
  repository. Covers the a priori workflow (Stages 1–5, Docker commands), study
  design reanalysis (Stages 6–8, pre-computed CSVs), fold-error interpretation,
  data schemas, PKML entity paths, molecule-level details, error messages,
  output file formats, adding a new mAb, and licence implications. Use when asked
  to run simulations, check accuracy, answer study-design questions, interpret
  outputs, troubleshoot errors, or adapt the workflow to a new antibody.
---

# PBPK mAb NAM Tutorial — skill

## 1. Repository purpose and two-objective structure

This repository is an end-to-end tutorial for **a priori PBPK prediction of
monoclonal antibody (mAb) pharmacokinetics** using the Open Systems Pharmacology
(OSP) Suite and R, and for **retrospective monkey PK study-design reanalysis**.
It is intended for pharmacometricians and modellers with doctoral-level
background who need a reproducible, open reference for large-molecule PBPK.

The repository has **two separate objectives** with independent folder trees and
stage numbering. Never conflate them.

**Objective 1 — A priori PBPK predictions** (`02_APriori_PBPK_Workflow/`)  
Can a PBPK model predict monkey and human mAb PK from in-vitro lab measurements
alone, before any in-vivo data? Tested retrospectively on 8 approved mAbs
across 5 targets.

| Stage | Script | What it does |
|---|---|---|
| 1 | `01_Setup_Configurations.qmd` | Validate data, resolve infusion durations, write configuration workbooks |
| 2 | `02_Run_Sims.qmd` | Load PKML models, apply parameters, run all monkey and human dose scenarios |
| 3 | `03_Process_Sims_Outputs.qmd` | Evaluate predictions: fold errors, PK endpoints, HTML report |
| 4 (optional) | `04_LocalSensitivityAnalysis.qmd` | One-way sensitivity of clearance to three TMDD parameters |
| 5 (optional) | `05_Supplementary_Fold_Error_Tornado_Plot.qmd` | Generate the tornado figure and source table |

The Docker `apriori` command runs Stages 1, 2, 3, and 5 in sequence.
Stage 4 runs separately via the `sensitivity` command.
**Stages 6, 7, and 8 are not available as Docker commands.**

**Objective 2 — Study design reanalysis** (`03_Study_Simulations/`)  
If a monkey study is still required, how small can it be? 100,000 virtual
profiles were simulated across group sizes, doses, and variability scenarios.
Results are pre-computed and committed; Stages 6–8 do not need to be re-run.

| Stage | Script | What it does |
|---|---|---|
| 6 | `Step1_Prepare_Study_Design_Inputs.qmd` | Build uncertainty draws and population inputs |
| 7 | `Step2_Run_Study_Design_Simulations.qmd` | Run 100k profiles (~hours; checkpointed) |
| 8 | `Step3_Postprocess_Study_Design_Results.qmd` | Calculate endpoints and design success rates |

---

## 2. Molecules in this repository

All 8 mAbs are intravenously administered. Know these details when answering
questions about specific molecules or comparing targets.

| Antibody | Target | IgG subclass | Species tested |
|---|---|---|---|
| Tocilizumab | IL-6R | Humanized IgG1 | Monkey, Human |
| Nivolumab | PD-1 | Human IgG4 | Monkey, Human |
| Pembrolizumab | PD-1 | Humanized IgG4 | Monkey, Human |
| Atezolizumab | PD-L1 | Humanized IgG1 (Fc-aglyco, no effector function) | Monkey, Human |
| Avelumab | PD-L1 | Human IgG1 | Monkey, Human |
| Adalimumab | TNF-α | Human IgG1 | Monkey, Human |
| Golimumab | TNF-α | Human IgG1 | Monkey, Human |
| Bevacizumab | VEGF-A | Humanized IgG1 | Monkey, Human |

The study design reanalysis (Stages 6–8) covers **Golimumab** (uncalibrated,
nominal a priori model) and **Nivolumab** (calibrated: a priori Anti-PD1
structure with FcRn Kd set to 0.39 µmol/L) only. No uncalibrated Nivolumab
arm is simulated.

---

## 3. TMDD model structure

The models use **full TMDD with an explicit drug–target complex compartment**
built in MoBi (`.mbp3`), exported as compiled PKML files (`.pkml`). The
MoBi project adds generic target-mediated drug disposition reactions to the
PK-Sim large-molecule PBPK scaffold. The six mechanistic inputs drive:

- FcRn recycling (FcRn binding affinity Kd)
- Target binding and complex formation (drug-target Kd, koff)
- Complex removal (complex internalization rate kint)
- Target turnover (target degradation rate kdeg)
- Target exposure level (target reference concentration)

Do not suggest Michaelis-Menten or quasi-steady-state TMDD approximations —
the full model is implemented and the simplifications are not used here.

---

## 4. The six mechanistic inputs — units and sources

| Input | PKML entity name | Units | Typical source |
|---|---|---|---|
| FcRn binding affinity | `mAb` | µmol/L | SPR, FcRn binding assay |
| Drug-target affinity (Kd) | `mAb-Target-InVitro` | µmol/L | SPR, biolayer interferometry |
| Drug-target dissociation rate (koff) | `mAb-Target-InVitro` | 1/min | SPR |
| Complex internalization rate (kint) | `Complex Internalization` | 1/h | Internalization assay |
| Target degradation rate (kdeg) | `Target degradation` | 1/h | Literature / assay |
| Target reference concentration | `Target` | nmol/L | Tissue-expression data, FACS |

**Critical:** entity names must match exactly. Any rename in PK-Sim or MoBi
must be propagated to the R scripts; a PKML file can still open after a rename
while the programmatic hand-off silently fails because R looks up entities by
exact path. Do not invent, estimate, or fill in missing values for any of these
six inputs.

---

## 5. Data file schemas

### `00_Data/Monkey/mAb_data.csv` and `00_Data/Human/mAb_data_human.csv`

Both files share the same 21-column schema. Missing values are coded as `"."`.

| Column | Type | Description |
|---|---|---|
| Study.Id | character | Publication reference (e.g. `"Tajiri 2024 Fig 1"`) |
| Subject.Id | integer | Individual subject identifier within the study |
| Organ | character | Always `"Venous Blood"` |
| Compartment | character | Always `"Plasma"` |
| Species | character | `"NHP"` (monkey) or `"Human"` |
| Gender | character | Sex or `"."` if not reported |
| Dose | numeric | Dose in mg/kg |
| Molecule | character | Exact antibody name (matches PKML and Parameters.xlsx) |
| Molecular.Weight | numeric | Molecular weight in g/mol (Da) |
| Time | numeric | Nominal time post-dose |
| Time.unit | character | `"hr"` |
| Measurement | numeric | Plasma concentration |
| Measurement.unit | character | `"ug/mL"` |
| Error | numeric | SD or CV or `"."` |
| LLOQ | numeric | Lower limit of quantification or `"."` |
| Route | character | See §6 for allowed values and duration assignment |
| Group.Id | character | Dose-group identifier or `"."` |
| Population | character | Population label or `"."` |
| Weight..kg. | numeric | Body weight in kg or `"."` |
| Height..cm. | numeric | Body height in cm or `"."` |
| Age..year.s.. | numeric | Age in years or `"."` |

**LLOQ handling:** observations where `Measurement < LLOQ` are present in the
file but excluded from fold-error evaluation. Do not remove or impute them.

### `00_Data/Monkey/Parameters.xlsx` and `00_Data/Human/Parameters_human.xlsx`

These workbooks hold the six mechanistic inputs per molecule. Preserve the
worksheet structure, column headers, and units exactly. Stage 1 validates
expected fields and will stop if a required column is missing or a unit
does not match.

---

## 6. Administration duration rules (Stage 1)

Stage 1 assigns simulation infusion duration from the `Route` column in the
data files using regex matching (case-insensitive). Stage 1 stops rather than
guessing for an unrecognised Route string; only IV records are included.

| Species | Condition | Assigned duration |
|---|---|---|
| Monkey | Any Route starting with `"iv"` (case-insensitive) (e.g. `"IV"`, `"IV Bolus"`) | 1 minute (bolus approximation) |
| Human | `molecule == "Adalimumab"` (any Route string) | 30 minutes — **molecule-specific rule, evaluated first** |
| Human | Route contains `"30min"` or `"30 min"` (regex `30\s*min`) | 30 minutes |
| Human | Route contains `"1hr"`, `"1 hr"`, `"1hour"`, or `"1 hour"` (regex `1\s*hr\|1\s*hour`) | 60 minutes |
| Human | Route contains `"2hr"`, `"2 hr"`, `"2hour"`, or `"2 hour"` (regex `2\s*hr\|2\s*hour`) | 120 minutes |
| Either | Any other string | **STOPS with an error** |

**The Adalimumab exception:** Human Adalimumab records use Route `"IV Infusion"` (no
duration embedded). This resolves to 30 minutes via the molecule-specific rule in
`resolve_infusion_minutes()`, which is evaluated **before** the regex rules. Every other
human mAb must embed the infusion duration in the Route string. A plain human `"IV"` or
`"IV Infusion"` Route for any molecule other than Adalimumab will stop the pipeline.

**Actual Route formats used in the committed data files:**
- Monkey: `"IV"`, `"IV Bolus"` — both match `^iv`.
- Human Pembrolizumab: `"IV 30min Infusion"` → 30 min.
- Human Nivolumab: `"IV 1hr Infusion"` → 60 min.
- Human Golimumab: `"IV 2hr Infusion"` → 120 min.
- Human Adalimumab: `"IV Infusion"` → 30 min (molecule-specific rule).

When adding a new mAb, use one of the recognised duration patterns above in the Route
string, or add a molecule-specific rule to `resolve_infusion_minutes()` in
`01_Setup_Configurations.qmd` before running Stage 1.

---

## 7. Configuration workbooks — generated vs inputs

Stage 1 **overwrites** three generated workbooks. Stage 1 is expected to
replace them; do not edit them manually, as your changes will be lost on the
next run.

| Workbook | Type | Notes |
|---|---|---|
| `Configurations/Applications.xlsx` | **Generated** (overwritten by Stage 1) | |
| `Configurations/ModelParameters.xlsx` | **Generated** (overwritten by Stage 1) | |
| `Configurations/Scenarios.xlsx` | **Generated** (overwritten by Stage 1) | |
| `Configurations/Individuals.xlsx` | **Input** (never overwritten) | Edit to add individual-level parameters |
| `Configurations/Populations.xlsx` | **Input** (never overwritten) | Edit to add population parameters |
| `ProjectConfiguration.xlsx` | Updated by Stage 1 (paths only) | Stage 1 writes repository-relative paths into this file |

If Stage 1 cannot overwrite a generated workbook, it stops. The fix is to close
the workbook in Excel and rerun.

---

## 8. Software versions and critical constraint

| Component | Pinned version in Docker | Required for reproduction |
|---|---|---|
| R | 4.5.1 | Scripts also verified with 4.6.1 |
| ospsuite | 12.4.2 | **12.4.x only — ospsuite 13 not supported** |
| esqlabsR | 5.6.0 | 5.6.0 or later within 5.x |
| rSharp | 1.2.3 | |
| Quarto | (conda-forge pinned) | |
| .NET runtime | 8.0 | Required by rSharp |
| PK-Sim / MoBi | 12.2 | For editing `.pksim5` / `.mbp3` projects only |

**ospsuite 13 is not supported.** Installing it produces the error
`"cannot add bindings to a locked environment"` in Stage 2. If `packageVersion("ospsuite")`
reports 13.x, reinstall 12.4.2:
```r
pak::pak("Open-Systems-Pharmacology/OSPSuite-R@v12.4.2")
```
The Docker image pins 12.4.2 and is not affected by this issue.

---

## 9. Rules for AI assistant behaviour

- **Never invent, estimate, or fill in** biological parameters, doses, or
  observed data. If a value is missing, say so and ask the user to supply it
  from the primary source.
- **Never edit** files under `00_Data/`, `01_Models/`, or the `.qmd` scripts
  unless the user explicitly requests that specific change.
- **Never choose or change** model structure or TMDD formulation.
- **Report a run as successful** only if the runner prints `MATCH` (for
  `apriori`) or finishes without a `STOPPED` line (all other commands). Quote
  the exact `STOPPED` line and the log path `_pbpk_logs/<stage>.log` otherwise.
- **Never report old results as new.** If Stage 2 did not record a new run
  folder, the pipeline stops; do not interpret previously committed results as
  the outcome of the current run.
- **Do not send** confidential or proprietary molecule information to any
  service the user has not approved.
- **For a study-design question**, read the relevant pre-computed CSV directly.
  Do not attempt to re-run Stages 6–8.

---

## 10. Prerequisites

- Repository cloned with `git clone` (not downloaded as a ZIP). The `apriori`
  and `compare` commands use `git` history to verify fold errors; a ZIP download
  has no history and the comparison will fail silently.
- Branch must be `main` (v0.2.1 or later). Running on `corrections_v0.2.0`
  produces `STOPPED: This checkout still has the v0.2.0 file-name bug`.
- Docker Desktop installed and running ("Engine running" in the system tray).
- Files `00_Data/Monkey/mAb_data.csv`, `00_Data/Human/mAb_data_human.csv`,
  `00_Data/Monkey/Parameters.xlsx`, and `00_Data/Human/Parameters_human.xlsx`
  must be present. The workflow also requires all PKML files under `01_Models/`.

---

## 11. Running the a priori workflow (Stages 1–5)

### Commands

| Command | Description | Approx. time |
|---|---|---|
| `apriori` | Stages 1 → 2 → 3 → 5; stops at first failure; refuses to reuse an old run; compares fold errors | ~6 min |
| `summary` | Within-2-fold counts by species and endpoint | seconds |
| `compare` | Compare current table with committed table only; no re-simulation | seconds |
| `sensitivity` | Stage 4 — one-way local sensitivity | ~15 min |
| `versions` | R, Quarto, rSharp, ospsuite, esqlabsR, .NET versions inside the image | seconds |
| `build` | Rebuild the Docker image explicitly | 15–30 min |
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

Note: `build` is handled by the launchers, not the container. To rebuild
without a launcher:
```
docker build --platform linux/amd64 -t pbpk-mab-nam docker
```

### First run

The first run downloads ~1 GB and builds the image (15–30 minutes).
The line `==> Building the 'pbpk-mab-nam' image` is expected — do not interrupt.
Apple Silicon Macs (M1/M2/M3/M4) run via Rosetta 2; launchers pass
`--platform linux/amd64` automatically. Subsequent runs start in seconds.

### Workflow

1. Run `versions` to confirm the environment is correct.
2. Run `apriori`. Do not interrupt. Expected duration ~6 minutes.
3. If it prints `MATCH` — run `summary` and report the accuracy table.
4. If it prints `DIFFERENT` or `STOPPED` — quote the exact output and the log
   path under `_pbpk_logs/`. Do not attempt to fix scientific inputs.
5. After a successful `apriori` run, outputs are:
   - Main report: `02_APriori_PBPK_Workflow/Scripts/03_Process_Sims_Outputs.html`
   - Fold-error table: `02_APriori_PBPK_Workflow/SimsOutputs/Tables/Supplement_Fold_Error_Tornado_Data.csv`
   - New simulation folder: path in `02_APriori_PBPK_Workflow/SimsOutputs/latest_simulation_run.txt`
6. After `sensitivity` (Stage 4): `02_APriori_PBPK_Workflow/Scripts/04_LocalSensitivityAnalysis.html`
7. The run modifies tracked files (configuration workbooks, HTML reports, tornado figure).
   To restore: `git checkout -- .` and delete the new timestamped folder under
   `02_APriori_PBPK_Workflow/SimsOutputs/SimulationResults/`.

---

## 12. PK endpoint definitions (exact, as calculated by Stage 3)

All calculations operate on matched observed sampling times. Observed data are
introduced only after simulations are complete (Stage 3 only).

| Metric | Definition |
|---|---|
| **Cmax** | Maximum concentration in the available profile |
| **AUC0-tlast** | Linear-up / log-down trapezoidal rule applied to both predicted and observed profiles at the same observed sampling times |
| **AUCinf** | AUClast + Clast / λz (terminal elimination rate constant) |
| **Clearance** | Dose / AUCinf; units are L/day/kg because dose is in mg/kg |
| **Fold error** | Predicted / Observed (not the inverse). Range 0.5–2.0 = within 2-fold |
| **Percent extrapolated** | 100 × (AUCinf − AUClast) / AUCinf |

**Evaluability rules:**
- Clearance is `"Evaluated"` only when percent extrapolated ≤ 20%. Profiles
  failing this threshold are marked `"Not evaluable"` and excluded from CL
  fold-error counts.
- AUC0-tlast and Cmax are evaluated regardless of the extrapolation fraction.
- Fewer clearance rows appear in the fold-error table than AUC or Cmax rows
  for this reason.

**Fold-error table columns** (`Supplement_Fold_Error_Tornado_Data.csv`):
`Species`, `Metric`, `Molecule`, `Dose_mg_kg`, `Fold_error` (predicted/observed),
`Log2_fold_error`, `Evaluation_status`.

---

## 13. Interpreting the accuracy summary

The `summary` command (and `compare`) uses this logic:
- Fold error = predicted / observed
- Within 2-fold: 0.5 ≤ fold error ≤ 2.0
- Reports N evaluated, N within 2-fold, and percentage — by species (Monkey,
  Human) and endpoint (AUC0-tlast, Cmax, Clearance)
- The published result is MATCH on all 132 evaluated scenario-endpoints

---

## 14. Local sensitivity analysis (Stage 4)

Stage 4 is a **local one-way sensitivity analysis**, not parameter fitting,
not a global uncertainty analysis, and not a dose–response model:

- **Parameters varied:** target reference concentration, kint, kdeg
- **Range:** 0.1× and 10× the a priori (central) value, one parameter at a time
- **Endpoint evaluated:** predicted clearance
- **Prerequisite:** Stages 1 and 2 must have completed. Stage 3 is not required.
- **Output:** `02_APriori_PBPK_Workflow/Scripts/04_LocalSensitivityAnalysis.html`

Do not describe Stage 4 as a parameter estimation step or a global sensitivity
analysis. The analysis does not use observed data and does not fit anything.

---

## 15. Stage 5 — tornado plot

Stage 5 reads the scenario-level table embedded in the Stage 3 HTML report.
It does **not** re-run simulations or recalculate PK endpoints. Outputs:

- `02_APriori_PBPK_Workflow/SimsOutputs/Figures/Supplement_Fold_Error_Tornado_Monkey_Human.png`
- `02_APriori_PBPK_Workflow/SimsOutputs/Tables/Supplement_Fold_Error_Tornado_Data.csv`

---

## 16. Complete error message catalog

| STOPPED / error message | Cause | Fix |
|---|---|---|
| `STOPPED: The repository is not mounted at /work.` | Docker volume mount missing or wrong path | Run from repo root with `-v "${PWD}:/work"` |
| `STOPPED: This checkout still has the v0.2.0 file-name bug.` | On branch `corrections_v0.2.0` or old commit | `git checkout main` |
| `STOPPED: Stage 2 did not record a new simulation run; stopping so old results are not reused.` | Stage 2 failed silently or completed but did not update `latest_simulation_run.txt` | Check `_pbpk_logs/02_Run_Sims.log` for the real error |
| `STOPPED: <stage> failed. Nothing after it was run. Full log: _pbpk_logs/<stage>.log` | A Quarto render failed | Read the log; first 5 error lines are shown above the STOPPED line |
| `DIFFERENT: see the rows above.` | Fold errors do not reproduce the published table | Not a software error; check if data or scripts have been modified |
| `cannot add bindings to a locked environment` (R error in Stage 2) | ospsuite 13 is installed | Reinstall ospsuite 12.4.2 |
| `Project root not found.` (R error) | Script not run from inside the repository folder | Run from the repo root or any subfolder |
| Stage 1 stops with "cannot replace workbook" | The workbook is open in Excel | Close it and rerun Stage 1 |
| Stage 1 stops with "unrecognised IV label" | Route column value not in the recognised list (see §6) | Add the correct Route label or add a duration rule to Stage 1 |
| `No committed table to compare with.` (compare output) | Repository was downloaded as ZIP, not cloned with git | Clone properly with `git clone` |

---

## 17. Output files — complete reference

### Stage 1 outputs
| File | Notes |
|---|---|
| `Configurations/Applications.xlsx` | Generated; overwrites previous |
| `Configurations/ModelParameters.xlsx` | Generated; overwrites previous |
| `Configurations/Scenarios.xlsx` | Generated; overwrites previous |
| `ProjectConfiguration.xlsx` | Updated paths section only |

### Stage 2 outputs
| File | Notes |
|---|---|
| `SimsOutputs/SimulationResults/<timestamp>/` | Scenario-level CSV and PKML simulation files |
| `SimsOutputs/latest_simulation_run.txt` | Manifest: name of the folder Stage 3 will use |

### Stage 3 outputs
| File | Notes |
|---|---|
| `Scripts/03_Process_Sims_Outputs.html` | Self-contained: obs/pred PK plots, fold-error tables, AUCinf diagnostics, session info |

### Stage 4 outputs
| File | Notes |
|---|---|
| `Scripts/04_LocalSensitivityAnalysis.html` | One-way sensitivity report |

### Stage 5 outputs
| File | Notes |
|---|---|
| `SimsOutputs/Figures/Supplement_Fold_Error_Tornado_Monkey_Human.png` | Tornado figure |
| `SimsOutputs/Tables/Supplement_Fold_Error_Tornado_Data.csv` | Source table for the figure |

### Stage 7 outputs (pre-computed; do not re-run)
| File | Notes |
|---|---|
| `03_Study_Simulations/SimsOutputs/Step2_Simulations/Checkpoints/` | 200 independent checkpoints (10 replicates each) |

### Stage 8 outputs (pre-computed; do not re-run)
| File | Notes |
|---|---|
| `03_Study_Simulations/SimsOutputs/Step3_Results/Tables/study_design_overall_success.csv` | Overall fraction within 2-fold by design |
| `03_Study_Simulations/SimsOutputs/Step3_Results/Tables/study_design_endpoint_success.csv` | Performance by endpoint |
| `03_Study_Simulations/SimsOutputs/Step3_Results/Tables/study_design_fold_error_summary.csv` | Fold errors by dose |
| `03_Study_Simulations/SimsOutputs/Step3_Results/Tables/study_design_replicate_matched_fold_error.csv` | Replicate-level fold errors (primary output) |
| `03_Study_Simulations/SimsOutputs/Step3_Results/Tables/study_design_replicate_matched_dense_truth.csv` | Replicate vs dense truth comparison |
| `03_Study_Simulations/SimsOutputs/Step3_Results/Tables/study_design_nominal_typical_fold_error.csv` | Per-replicate nominal-reference fold errors |
| `03_Study_Simulations/SimsOutputs/Step3_Results/Tables/study_design_nominal_typical_fold_error_summary.csv` | Secondary nominal-reference fold errors (summarised) |
| `03_Study_Simulations/SimsOutputs/Step3_Results/Tables/study_design_excluded_failed_profiles.csv` | Documents the two excluded Golimumab 3 mg/kg profiles |
| `03_Study_Simulations/SimsOutputs/Step3_Results/Tables/study_design_analysis_qc.csv` | QC and diagnostics |

---

## 18. Study design questions (Stages 6–8) — pre-computed results

**Do not attempt to re-run Stages 6, 7, or 8.** Stage 7 takes several hours
and is not available as a Docker command. All results are already committed.

### What is covered

- Molecules: **Golimumab** (uncalibrated) and **Nivolumab** (FcRn Kd = 0.39 µmol/L)
- Doses: **0.1, 1, 3, 10, 30 mg/kg**
- Designs: **2, 3, or 5 dose groups** (dose sets: {1,10}; {0.1,1,10}; all five)
- Animals per group: **2, 3, or 6** (sampled without replacement within group)
- Variability scenarios: **30% CV** and **60% CV** for the five shared mechanistic inputs
- Endpoints: AUC0-28d, Cmax, Terminal clearance
- 100 replicates per molecule and variability scenario; 50 monkeys per replicate

### Primary vs secondary fold-error reference — critical distinction

| Reference type | Definition | File |
|---|---|---|
| **Primary (replicate-matched dense)** | Sparse study mean vs arithmetic mean of the evaluable replicate-matched dense individual endpoints for the **same molecule, variability scenario, replicate, and dose**. This is the primary design-performance metric. | `study_design_replicate_matched_fold_error.csv` |
| **Secondary (nominal typical-subject)** | Sparse study mean vs a fixed nominal typical-subject endpoint. Captures design error plus the shift of that replicate's truth from the nominal model. Not substituted for the primary. | `study_design_nominal_typical_fold_error_summary.csv` |

Do not confuse these two references or report the secondary as the main result.

### Failed-profile exclusion

Two Golimumab 3 mg/kg profiles produced no output after retry and were
excluded only from their matched dose cells. The other doses for those monkeys
remain in the analysis. This is documented explicitly in the Stage 8 HTML report
and QC table.

### How to answer a study design question

1. Read the relevant CSV directly — do not run any simulation.
2. Filter by molecule, dose (Dose_mg_kg), design, and N_per_group.
3. Report `Fraction_within_2fold` from `study_design_overall_success.csv`.
4. By endpoint: use `study_design_endpoint_success.csv`.
5. By dose fold error: use `study_design_fold_error_summary.csv`.
6. Always state that results are conditional on the Golimumab and Nivolumab
   truth models, the configured variability assumptions, and the 0.5–2-fold
   criterion as a tutorial threshold — not a universal design standard.

### Example

"What happens at 0.1 mg/kg with 2 monkeys per group?"  
Read `study_design_fold_error_summary.csv`, filter Dose_mg_kg = 0.1,
N_per_group = 2, report Fraction_within_2fold for each molecule, endpoint,
and CV scenario. Check `study_design_overall_success.csv` for overall success.

### Checkpoint recovery (Stage 7)

If Stage 7 was interrupted: rerender `Step2_Run_Study_Design_Simulations.qmd`.
Valid checkpoints are reused automatically based on the saved Step 1 input
checksum. Set `STUDY_DESIGN_FORCE_RERUN=true` **only** for a deliberate full
recomputation. Incompatible inputs (changed Step 1 outputs) cannot be silently
mixed with an earlier run — the checksum check prevents this.

---

## 19. Applying the workflow to a new mAb — step-by-step

An AI assistant may walk through this checklist with the user. The user
retains scientific responsibility for every value and decision.

1. **Define the mAb and target:** species, route, dose levels, infusion or
   bolus duration, molecular weight, target tissue and localisation. Confirm
   whether a compatible PKML model already exists or must be built.

2. **Source the six mechanistic inputs** (see §4). Record each value with
   its assay method, species, conditions, unit, and primary literature
   citation. Do not borrow a value from another mAb or target without explicit
   scientific justification. List uncertainty range if available.

3. **Prepare or obtain the PKML model:** A PKML from the same target can be
   reused for another antibody against that target only after confirming that
   the model structure, entity naming, and expression profiles remain
   appropriate. If a new target is added, build the PKML in PK-Sim and MoBi
   following the `01_Models/README.qmd` tutorial.

4. **Add data to the input files (preserve exact schema from §5):**
   - New rows in `mAb_data.csv` (monkey) and/or `mAb_data_human.csv`
   - New worksheet(s) or rows in `Parameters.xlsx` and `Parameters_human.xlsx`
   - Confirm the Route label is in the recognised list (§6)
   - Confirm Molecular.Weight is in g/mol and matches the Parameters workbook

5. **Add the new PKML file(s)** to the appropriate subfolder under `01_Models/`.
   Do not rename existing PKML entity names — any rename must also update every
   R script that references that entity path.

6. **Update `ProjectConfiguration.xlsx`** to include the new molecule's PKML
   path. Run Stage 1 to regenerate configuration workbooks, then run Stages 2
   and 3. Inspect the HTML report for warnings, missing-profile indicators, and
   AUCinf extrapolation fractions before interpreting fold errors.

**LLM-appropriate tasks during adaptation:**
- Extract candidate parameter values from user-supplied papers into a structured
  evidence table
- Draft code changes that update molecule-specific constants consistently
- Write validation checklists and small test cases
- Document assumptions and unit conversions

**LLM must not:**
- Generate or guess any mechanistic parameter value
- Choose model structure without domain review
- Transfer a literature value across species, targets, assay formats, or disease
  settings without explicit user justification

---

## 20. Licence and citation

| Content | Licence | Implication |
|---|---|---|
| R and Quarto scripts | MIT | Can copy, modify, redistribute, use commercially without restriction |
| Data, models, documentation, figures | CC BY 4.0 | Must credit this repository and the accompanying publication |
| Observed PK data | CC BY 4.0 + cite original studies | Digitised from published studies; original sources must also be cited |
| OSP packages (ospsuite, esqlabsR, rSharp) | GPL-2.0 | Cannot be combined with proprietary code in a closed binary without licence compliance |
| PK-Sim and MoBi desktop tools | GPL-2.0 | Same |

**Citation:** The accompanying publication is not yet published. Until it is,
cite the repository URL and the commit hash (or release tag) used. When the
paper is published, cite both the paper and the repository. Always additionally
cite the primary literature sources for the observed concentration data (listed
in `00_Data`) and for each mechanistic parameter value (listed in the parameter
workbooks).

---

## 21. What this skill does not cover

- **Adding a new antibody or target** beyond the six-step checklist in §19:
  the actual model building in PK-Sim and MoBi requires those tools locally.
- **Editing model structure:** PK-Sim and MoBi are required; they are not in
  the Docker image.
- **Study design for molecules other than Golimumab and Nivolumab:** the
  pre-computed tables cover only these two as configured in Stage 6.
- **ospsuite 13 compatibility:** not supported; see §8.
- **Graphical inspection of `.pksim5` or `.mbp3` files:** requires the desktop
  OSP Suite applications.
