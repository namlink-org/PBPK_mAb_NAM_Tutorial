# Objective 1 tutorial: a priori monkey and human PBPK predictions

This folder contains the executable tutorial for Objective 1 of the manuscript: generate a priori monkey and human pharmacokinetic predictions from prepared PK-Sim/MoBi simulation files, then compare the predictions with observed data.

## Starting point

The tutorial starts after two upstream tasks are complete:

1. The species- and target-specific PK-Sim/MoBi models have been exported as PKML files under `../01_Models/`.
2. The observed PK data and literature-derived mechanistic parameters have been formatted under `../00_Data/`.

Creating the PK-Sim/MoBi models and formatting the source data are upstream
tasks. The model-building workflow is documented in `../01_Models/README.qmd`;
this tutorial starts from the compiled PKML files and prepared data.

## What makes the predictions a priori

The PBPK simulations use the prepared model structure, species physiology, and literature- or in vitro-derived molecule and target parameters. Observed concentration measurements are not used to fit or calibrate the PBPK model. In this retrospective example, the observed datasets are used only to identify the dose scenarios and to evaluate the predictions after simulation.

## Run order

Render the core Quarto files in `Scripts/` in numeric order, followed by either
optional analysis when needed:

1. `01_Setup_Configurations.qmd` validates the inputs and creates the esqlabsR configuration workbooks.
2. `02_Run_Sims.qmd` creates and runs all configured monkey and human simulations.
3. `03_Process_Sims_Outputs.qmd` produces concentration-time figures, noncompartmental PK metrics, fold errors, accuracy summaries, and AUC extrapolation diagnostics.
4. `04_LocalSensitivityAnalysis.qmd` is an optional advanced step that changes
   target reference concentration, `kint`, and `kdeg` one at a time to 0.1 or
   10 times the a priori value and evaluates predicted clearance. It requires
   Steps 1 and 2; Step 3 is not a prerequisite.
5. `05_Supplementary_Fold_Error_Tornado_Plot.qmd` is an optional reporting step
   that reads the complete scenario-level results embedded in the rendered
   Step 3 report and creates the supplementary fold-error tornado plot. It does
   not rerun simulations or recalculate endpoints.

Each Quarto file contains its own purpose, functions, inputs, outputs, checks,
and interpretation notes; none sources a separate helper script. The rendered
HTML uses embedded resources, so each tutorial is a single portable file and
does not require a companion `<tutorial-name>_files` folder. Figures and tables
from Steps 3 and 4 are displayed directly in their HTML reports. Step 5 also
exports its final figure and source table as standalone files for manuscript
use.

## Administration durations

Applications are configured from the study route labels in the formatted datasets:

- monkey IV and IV-bolus records: 1-minute bolus approximation;
- adalimumab human IV infusion: 30 minutes;
- pembrolizumab human IV infusion: 30 minutes;
- human routes labeled `IV 1hr Infusion`: 60 minutes;
- human routes labeled `IV 2hr Infusion`: 120 minutes.

The configuration script stops if it encounters an IV route whose duration cannot be resolved. This prevents an undocumented administration assumption from entering the predictions.

## Main outputs

The workflow writes the required configuration and simulation intermediates,
plus one self-contained HTML report per tutorial:

- `Configurations/`: the application, model-parameter, and scenario workbooks
  required to create the simulations;
- `SimsOutputs/SimulationResults/<run>/`: scenario-level simulation CSV and PKML files;
- `SimsOutputs/latest_simulation_run.txt`: the simulation folder selected by downstream scripts;
- `Scripts/<tutorial-name>.html`: one self-contained tutorial report with all
  displayed figures, tables, settings, and R session information embedded;
- `SimsOutputs/Figures/Supplement_Fold_Error_Tornado_Monkey_Human.png`: the
  standalone supplementary plot created by Step 5; and
- `SimsOutputs/Tables/Supplement_Fold_Error_Tornado_Data.csv`: the source table
  used by that plot.

The Step 3 evaluation and Step 4 sensitivity figures and tables remain embedded
in their rendered HTML reports. The Step 5 outputs are intentionally written
separately because they are manuscript-facing deliverables.

## Software

The manuscript results were generated with R 4.5.1, PK-Sim 12.2, MoBi 12.2, esqlabsR 5.6.0, and ospsuite 12.4.2. The scripts report the installed R package versions at run time and require esqlabsR 5.6.0 or later and ospsuite 12.4.2 or later. Newer versions can contain numerical or interface changes, so record the versions used for every reproduced analysis.
