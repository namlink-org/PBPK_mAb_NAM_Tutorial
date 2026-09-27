# PBPK mAb NAM Tutorial

This repository contains an end-to-end tutorial for using physiologically based
pharmacokinetic (PBPK) models to predict monoclonal antibody (mAb)
pharmacokinetics and to explore reduced monkey pharmacokinetic (PK) study
designs. The workflow combines PK-Sim and MoBi model development with
programmatic simulation, evaluation, and study-design analysis in R.

The supplied analysis has two primary objectives:

1. Generate monkey and human mAb PK predictions with PK-Sim/MoBi without
   calibrating the models with in vivo PK profiles.
2. Use the PBPK models to explore opportunities to reduce the number
   of animals and dose groups in exploratory monkey PK studies.

A secondary objective is to evaluate the prediction workflow retrospectively
using eight intravenously administered mAbs across five targets. The analysis
compares predicted and observed concentration-time profiles and PK endpoints,
then uses Golimumab as a worked example to show how physiological variability
and uncertainty in mechanistic inputs affect the performance of candidate study
designs.

Observed concentration data are not used to fit or calibrate the PBPK models.
They are used retrospectively to define the evaluated dose scenarios and to
compare predictions with observations after simulations have been completed.
The reduced-study analysis is also model-conditional: it treats the nominal,
uncalibrated Golimumab model as the reference for the simulation exercise.

## Workflow at a glance

The repository implements the following stages:

1. Collect and format observed PK data and molecule- and target-specific
   mechanistic inputs.
2. Build species- and target-specific large-molecule PBPK models in PK-Sim,
   add target-mediated drug disposition (TMDD) reactions in MoBi, and export
   compiled PKML simulations.
3. Use R to configure and run a priori monkey and human predictions
4. Compare the saved predictions with observed PK data.
5. Cross virtual-monkey physiological variability with uncertainty in the six
   mechanistic inputs, simulate candidate studies, and compare reduced designs
   with a rich nominal-model reference.

## Repository organization

```text
PBPK_mAb_NAM_Tutorial/
|-- 00_Data/
|   |-- Monkey/                  Prepared monkey PK and parameter inputs
|   |-- Human/                   Prepared human PK and parameter inputs
|   `-- Extra/                   Ancillary data not read by the main workflow
|-- 01_Models/
|   |-- PK-Sim_Mobi_Files_*/     Editable PK-Sim and MoBi projects
|   |-- PKML_Files_*/            Simulation files used by R to simulate different scenarios and parameters
|   `-- Snapshots/               Not used in workflow
|-- 02_APriori_PBPK_Workflow/
|   |-- Configurations/          esqlabsR configuration workbooks
|   |-- Scripts/                 A priori simulation and evaluation tutorial scripts
|   `-- SimsOutputs/             Simulation runs and exported results
|-- 03_Study_Simulations/
|   |-- Scripts/                 Golimumab study-design simulations
|   `-- SimsOutputs/             Checkpoints, profiles, tables, and figures
`-- README.md                    This master guide
```

### `00_Data`

The main workflow reads the following prepared inputs:

- `Monkey/mAb_data_clean.csv`: monkey concentration-time data and study
  metadata used to define and evaluate scenarios;
- `Human/mAb_data_human.csv`: human concentration-time data and study metadata;
- `Monkey/Parameters.xlsx`: monkey molecule- and target-specific mechanistic
  inputs and their sources;
- `Human/Parameters_human.xlsx`: corresponding human inputs.

`Monkey/mAb_data.csv` and `Extra/mAb_data_evolocumab.csv` are not read by the
current executable workflow. Preserve the column and worksheet structures of
the files that are read because the Quarto scripts validate expected fields.

### `01_Models`

This folder contains editable PK-Sim (`.pksim5`) and MoBi (`.mbp3`) projects,
compiled PKML simulations, and the illustrated model-building tutorial. Models
are organized by species and target: IL-6R, PD-1, PD-L1, TNFA, and VEGFA.

The compiled target-specific PKML files are the hand-off to the R workflow.
The supplied files can be used directly to reproduce the analysis. Rebuilding
them is necessary only when changing model structure, target expression, or
other graphical model definitions. See the detailed
[`01_Models` tutorial](01_Models/README.qmd) or its rendered
[`README.html`](01_Models/README.html).

### `02_APriori_PBPK_Workflow`

This is the executable workflow for a priori monkey and human PBPK predictions.
It creates configuration workbooks, runs the configured simulations, calculates
PK endpoints and fold errors, and provides optional sensitivity and
supplementary analyses. See the
[`02_APriori_PBPK_Workflow` README](02_APriori_PBPK_Workflow/README.md).

### `03_Study_Simulations`

This folder contains the Golimumab worked example for exploring smaller monkey
PK studies. It generates a virtual population and uncertain parameter sets,
resamples candidate designs, creates a rich nominal-model reference, and
calculates fold-error and two-fold coverage summaries. See the
[`03_Study_Simulations` README](03_Study_Simulations/README.md).

## Software and installation

The manuscript analysis used the following versions:

| Component | Version used |
|---|---:|
| R | 4.5.1 |
| PK-Sim | 12.2 |
| MoBi | 12.2 |
| esqlabsR | 5.6.0 |
| ospsuite | 12.4.2 |
| Quarto | Not pinned in this repository |

The scripts accept `esqlabsR` 5.6.0 or later and `ospsuite` 12.4.2 or later,
but later versions may introduce interface or numerical changes. Use the
versions above when exact reproduction is the goal, and retain the package
versions recorded in each rendered report.

### 1. Install PK-Sim and MoBi

This workflow is designed for Windows because the editable OSP Suite projects
are built with the PK-Sim and MoBi desktop applications.

1. Follow the official [OSP Suite installation
   instructions](https://docs.open-systems-pharmacology.org/open-systems-pharmacology-suite/getting-started).
2. Install both PK-Sim and MoBi. Administrator access and a restart may be
   required.
3. To rebuild or inspect target-expression profiles, download the
   [PK-Sim gene-expression databases](https://github.com/Open-Systems-Pharmacology/Gene-Expression-Databases/releases),
   place them in a stable shared location, and connect them in PK-Sim Options.
4. Confirm that the required species and target genes can be queried before
   creating or modifying expression profiles.

Use OSP Suite 12.2 to edit the supplied project files when exact compatibility
is required. Opening and saving older projects in a newer release can update
their format. The R simulation workflow does not require the graphical projects
to be rebuilt when the supplied PKML files are used unchanged.

### 2. Install R and Quarto

Install 64-bit R 4.5.1 for the closest match to the recorded analysis, followed
by [Quarto](https://quarto.org/docs/get-started/). RStudio or another editor is
optional; the workflow can be run entirely from PowerShell with the Quarto
command-line interface.

The OSP R packages communicate with .NET through `rSharp`. Before installing
them, follow the current Windows prerequisites in the
[`rSharp` installation instructions](https://github.com/Open-Systems-Pharmacology/rSharp#installation),
including the required Microsoft Visual C++ Redistributable and .NET runtime.
Those external runtime versions are not pinned in this repository.

### 3. Install the R packages

Start R and run the following commands. The first command installs packages
used directly by the tutorial documents. The two `pak` commands select the
versions used for the manuscript analysis and install their dependencies.

```r
install.packages(c(
  "pak",
  "data.table",
  "dplyr",
  "ggplot2",
  "knitr",
  "openxlsx",
  "purrr",
  "readr",
  "rvest",
  "scales",
  "stringr",
  "tibble",
  "tidyr",
  "xml2"
))

pak::pak("Open-Systems-Pharmacology/OSPSuite-R@v12.4.2")
pak::pak("esqLABS/esqlabsR@v5.6.0")
```

If exact tagged installation is not possible on the target computer, use the
official OSP R package installation guidance and install versions that meet the
minimum checks in the scripts. Record any deviation from the versions above.

### 4. Verify the installation

In R, verify that the two simulation packages load and record their versions:

```r
library(ospsuite)
library(esqlabsR)

packageVersion("ospsuite")
packageVersion("esqlabsR")
sessionInfo()
```

In PowerShell, verify that Quarto can find the R installation:

```powershell
quarto check
```

Microsoft Excel is not required to execute the scripts because the workbooks
are read and written with `openxlsx`. Excel is useful for inspecting the
configurations, but any generated workbook must be closed before it is
overwritten.

## Model inputs and the PKML hand-off

Each molecule-species combination requires six mechanistic inputs. The entity
names and units below must remain aligned between the input workbooks, the
PK-Sim/MoBi models, and the R configuration scripts.

| Input | Model entity | Expected unit |
|---|---|---:|
| FcRn binding affinity | `mAb` | micromol/L |
| Drug-target binding affinity (`Kd`) | `mAb-Target-InVitro` | micromol/L |
| Drug-target dissociation rate (`koff`) | `mAb-Target-InVitro` | 1/min |
| Complex internalization rate (`kint`) | `Complex Internalization` | 1/h |
| Target degradation rate (`kdeg`) | `Target degradation` | 1/h |
| Target reference concentration | `Target` | nmol/L |

The model-building sequence is:

```text
PK-Sim project (.pksim5)
  -> MoBi project extended with generic TMDD reactions (.mbp3)
  -> compiled target- and species-specific simulation (.pkml)
  -> R-based configuration, simulation, and evaluation
```

Do not rename the antibody, target, complex, reaction, or parameter entities
without making the matching changes in the R scripts. A PKML file may still
open after a rename while the programmatic hand-off fails because the scripts
look up these entities by exact path.

## Run the complete analysis

Run the commands from the repository root. The scripts can also locate the
project from a subfolder, but the folder names `00_Data`, `01_Models`,
`02_APriori_PBPK_Workflow`, and `03_Study_Simulations` must not be changed.

### Before starting

1. Confirm that the four main prepared data files and the compiled PKML files
   are present.
2. Close `ProjectConfiguration.xlsx` and the workbooks under `Configurations/`
   if they are open in Excel.
3. Decide whether to preserve the supplied outputs. Configuration files and
   fixed-name study-simulation outputs can be replaced by a rerun; a priori
   simulation results are written to timestamped run folders.
4. Use the supplied PKML files for direct reproduction. Follow the manual
   `01_Models` tutorial first only when the models themselves must be rebuilt.

### Stage 1: Build the a priori simulation configurations

```powershell
quarto render ".\02_APriori_PBPK_Workflow\Scripts\01_Setup_Configurations.qmd"
```

This step validates the prepared data and PKML paths, resolves administration
durations, and writes:

- `Configurations/Applications.xlsx`;
- `Configurations/ModelParameters.xlsx`;
- `Configurations/Scenarios.xlsx`;
- updated repository-relative paths in `ProjectConfiguration.xlsx`.

It deliberately replaces the three generated configuration workbooks. The
supplied `Individuals.xlsx` and `Populations.xlsx` remain inputs to later
steps.

Administration durations are derived from the route labels in the prepared
data. Monkey IV and IV-bolus records use a one-minute bolus approximation;
adalimumab and pembrolizumab human infusions use 30 minutes; human routes
explicitly labeled as one- or two-hour infusions use 60 or 120 minutes. The
script stops rather than inventing a duration for an unrecognized IV label.

### Stage 2: Run the a priori monkey and human simulations

```powershell
quarto render ".\02_APriori_PBPK_Workflow\Scripts\02_Run_Sims.qmd"
```

This step loads the compiled PKML models, applies the configured parameters,
and runs every monkey and human dose scenario. It writes scenario-level CSV and
PKML files to a timestamped folder under
`02_APriori_PBPK_Workflow/SimsOutputs/SimulationResults/` and records the
selected folder in `SimsOutputs/latest_simulation_run.txt`. Downstream scripts
use this manifest rather than guessing which run to process.

### Stage 3: Evaluate the a priori predictions

```powershell
quarto render ".\02_APriori_PBPK_Workflow\Scripts\03_Process_Sims_Outputs.qmd"
```

This step loads the run named by `latest_simulation_run.txt` and then introduces
the observed concentration data for evaluation. It produces a self-contained
HTML report containing:

- observed-versus-predicted concentration-time plots;
- Cmax, AUC0-tlast, AUCinf, and clearance calculations;
- predicted/observed fold errors and two-fold accuracy summaries;
- AUCinf extrapolation diagnostics;
- complete scenario- and profile-level result tables;
- the R session information.

Observed and predicted AUC0-tlast are evaluated on matched observed sampling
times. Clearance is treated as evaluable only when the extrapolated fraction of
the observed AUCinf is no greater than 20%.

### Optional Stage 4: Run the local sensitivity analysis

```powershell
quarto render ".\02_APriori_PBPK_Workflow\Scripts\04_LocalSensitivityAnalysis.qmd"
```

This optional analysis changes target reference concentration, `kint`, and
`kdeg` one at a time to 0.1 or 10 times the a priori value and evaluates the
effect on predicted clearance. It is a local one-way sensitivity analysis, not
parameter fitting or a global uncertainty analysis. It requires Stages 1 and 2;
Stage 3 is not a prerequisite.

### Optional Stage 5: Create the supplementary fold-error tornado plot

```powershell
quarto render ".\02_APriori_PBPK_Workflow\Scripts\05_Supplementary_Fold_Error_Tornado_Plot.qmd"
```

This script reads the complete scenario-level table embedded in
`03_Process_Sims_Outputs.html`. It does not rerun simulations or recalculate PK
endpoints. It writes the plot and its source table under
`02_APriori_PBPK_Workflow/SimsOutputs/Figures/` and `Tables/`.

### Stage 6: Generate the Golimumab monkey study-simulation profiles

```powershell
quarto render ".\03_Study_Simulations\Scripts\Step1_APriori_Monkey_Study_Design_Simulations.qmd"
```

The default run:

- loads the completed a priori `Golimumab_Monkey_3_mpk` configuration;
- generates 50 virtual monkeys;
- draws 100 positive parameter sets at 30% and 50% coefficient of variation;
- crosses every parameter set with all 50 monkeys;
- simulates 0.1, 1, 3, 10, and 30 mg/kg;
- creates 50,000 concentration-time profiles before sparse sampling;
- resamples designs with 2, 3, or 5 dose groups and 2, 3, or 6 animals per
  group using a fixed sampling schedule;
- saves simulation records, input draws, diagnostic tables, figures, and
  resumable checkpoints under `03_Study_Simulations/SimsOutputs/`.

The simulation is batched and checkpointed. If rendering is interrupted, run
the same command again; validated completed batches are reused. Persistent
simulation failures are written to a diagnostic CSV and excluded explicitly.

The following PowerShell environment variables can change the computational
controls before rendering. Their defaults are already set in the script, so
they do not need to be defined for the manuscript-scale run.

```powershell
$env:PBPK_TUTORIAL_N_PARAMETER_SETS = "100"
$env:PBPK_TUTORIAL_PARAMETER_SETS_PER_BATCH = "10"
$env:PBPK_TUTORIAL_N_REPLICATES = "1000"
$env:PBPK_TUTORIAL_FORCE_RERUN = "false"
```

Set `PBPK_TUTORIAL_FORCE_RERUN=true` only when all Step 1 simulation batches
should be recomputed instead of reused.

### Stage 7: Calculate endpoints and fold errors for reduced studies

```powershell
quarto render ".\03_Study_Simulations\Scripts\Step2_Process_and_Calculate_Fold_Error.qmd"
```

This step reads the saved Step 1 R data object rather than rerunning the 50,000
profiles. It creates a densely sampled, typical-subject reference for the
nominal Golimumab model, calculates AUC0-28d, Cmax, and terminal clearance for
the rich and sparse profiles, and resamples the candidate designs. Outputs are
written under `03_Study_Simulations/SimsOutputs/Step2_Fold_Error/` and include:

- rich reference concentration profiles and PK endpoints;
- sparse individual endpoints;
- replicate-level fold errors;
- fold-error summaries;
- endpoint-level and overall two-fold coverage tables;
- the fold-error figure;
- a self-contained HTML report with settings and session information.

The two-fold interval is a prespecified tutorial criterion, not a universal
decision threshold. The results describe precision under the specified model,
input distributions, population, dose grid, and sampling schedule.

## Minimal reproduction command sequence

With the supplied PKML models and prepared data, the core end-to-end analysis is:

```powershell
quarto render ".\02_APriori_PBPK_Workflow\Scripts\01_Setup_Configurations.qmd"
quarto render ".\02_APriori_PBPK_Workflow\Scripts\02_Run_Sims.qmd"
quarto render ".\02_APriori_PBPK_Workflow\Scripts\03_Process_Sims_Outputs.qmd"
quarto render ".\03_Study_Simulations\Scripts\Step1_APriori_Monkey_Study_Design_Simulations.qmd"
quarto render ".\03_Study_Simulations\Scripts\Step2_Process_and_Calculate_Fold_Error.qmd"
```

Add the two optional `02_APriori_PBPK_Workflow` scripts when reproducing the
local-sensitivity and supplementary tornado-plot analyses.

## Reproducibility and quality checks

- Every Quarto file contains its own purpose, inputs, outputs, validation
  checks, and interpretation notes; the reports embed figures and session
  information.
- The scripts locate the repository root instead of relying on a user-specific
  working directory.
- The a priori simulation step records the exact timestamped output folder in
  `latest_simulation_run.txt`.
- The study-simulation scripts use fixed seeds, record their settings, save
  parameter draws and population records, and checkpoint expensive batches.
- The repository does not include an `renv` lockfile. Match the recorded
  package versions when exact reproduction matters.
- Review warnings, failed-profile logs, inventory tables, and package versions
  before interpreting any result.

## Troubleshooting

### Project root not found

Run Quarto from this repository or one of its subfolders and retain the four
main numbered directory names. The scripts identify the project from those
folders.

### A generated workbook cannot be replaced

Close the workbook in Excel and rerun Stage 1. The configuration script is
expected to overwrite its generated files.

### A downstream script cannot find a simulation run

Run `02_APriori_PBPK_Workflow/Scripts/02_Run_Sims.qmd` successfully and confirm that
`02_APriori_PBPK_Workflow/SimsOutputs/latest_simulation_run.txt` contains the
name of an existing timestamped folder.

### A PKML parameter or output path is missing

Check that the intended target-specific PKML file was used and that entity
names and paths match the six-input mapping above. If a PK-Sim or MoBi entity
was renamed, update the matching R path deliberately.

### The study-simulation render was interrupted

Rerun the same Step 1 command. Do not delete the checkpoint directory unless a
fresh run is intended. Use `PBPK_TUTORIAL_FORCE_RERUN=true` only for a deliberate
complete recomputation.

### Package or runtime loading fails

Confirm the R version, installed package versions, the Windows prerequisites
for `rSharp`, and the system locale guidance in the official OSP package
documentation. Run the small package-loading check before starting the full
simulation workflow.

## Applying the workflow to another mAb

The following items must be supplied or reviewed explicitly:

1. The mAb target, molecular weight, species, route, dose levels, infusion or
   bolus duration, and intended context of use.
2. The six mechanistic inputs, with units, species, assay conditions, source,
   method, and an evidence-based uncertainty description.
3. The target's tissue-expression pattern, reference concentration,
   localization, turnover, internalization, and any soluble-target or shedding
   behavior that changes the appropriate model structure.
4. A compatible species- and target-specific PK-Sim/MoBi model and compiled
   PKML file. A model can be reused for another antibody against the same target
   only after confirming that its structure and entity mappings remain
   appropriate.
5. New rows in the prepared PK data files and parameter workbooks, preserving
   their existing schema. Observed PK data are required for retrospective
   evaluation but should remain outside model calibration if the goal is an a
   priori prediction.
6. Dose, sampling, uncertainty, population, and decision criteria appropriate
   to the new question. The current `03_Study_Simulations` scripts are written
   specifically for Golimumab and contain hard-coded molecule names, source
   scenario, dose grid, output filenames, and reference assumptions that must
   be changed together.

### Appropriate uses of an LLM

A large language model can accelerate the adaptation while the modeler retains
scientific control. Useful tasks include:

- extracting candidate parameter values and assay context from user-supplied
  documents into a structured evidence table;
- drafting code changes that replace the Golimumab-specific constants and file
  names consistently in both study-simulation scripts;
- creating validation checklists and small test cases before launching the full
  virtual-population run;
- documenting assumptions, uncertainty distributions, and changes
  made for the new mAb.

An LLM should not generate/make-up for missing biological parameters, choose a model structure
without domain review, or treat a literature value as transferable across
species, targets, assay formats, or disease settings without justification.
Every extracted value should be checked against the primary source; every unit
conversion and parameter path should be verified; and all generated code should
be reviewed in a version-controlled branch and exercised first with a small
test run. Do not send confidential or proprietary molecule information to an
LLM service that has not been approved for that data.

A productive request to an LLM should provide the existing file schemas, the
new mAb and target, the six sourced mechanistic inputs, intended species and
routes, the PKML entity paths, the proposed dose and sampling design, and the
decision criteria. Ask for a traceable change plan and validation report in
addition to code changes. This keeps the LLM focused on reproducible adaptation
instead of unsupported scientific inference.
