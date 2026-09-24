# Objective 1 tutorial: a priori monkey and human PBPK predictions

This folder contains the executable tutorial for Objective 1 of the manuscript: generate a priori monkey and human pharmacokinetic predictions from prepared PK-Sim/MoBi simulation files, then compare the predictions with observed data.

## Starting point

The tutorial starts after two upstream tasks are complete:

1. The species- and target-specific PK-Sim/MoBi models have been exported as PKML files under `../01_Models/`.
2. The observed PK data and literature-derived mechanistic parameters have been formatted under `../00_Data/`.

Creating the PK-Sim/MoBi models and formatting the source data are intentionally outside this tutorial. They will be documented separately.

## What makes the predictions a priori

The PBPK simulations use the prepared model structure, species physiology, and literature- or in vitro-derived molecule and target parameters. Observed concentration measurements are not used to fit or calibrate the PBPK model. In this retrospective example, the observed datasets are used only to identify the dose scenarios and to evaluate the predictions after simulation.

## Run order

Render the Quarto files in `Scripts/` in numeric order:

1. `01_Setup_Configurations.qmd` validates the inputs and creates the esqlabsR configuration workbooks.
2. `02_Run_Sims.qmd` creates and runs all configured monkey and human simulations.
3. `03_Process_Sims_Outputs.qmd` produces concentration-time figures, noncompartmental PK metrics, fold errors, accuracy summaries, and AUC extrapolation diagnostics.
4. `04_SA.qmd` is an optional advanced step that performs the one-way sensitivity analysis reported in Supplementary Material S1.6.

Each Quarto file contains its own purpose, functions, inputs, outputs, checks,
and interpretation notes; none sources a separate helper script. The rendered
HTML uses embedded resources, so each tutorial is a single portable file and
does not require a companion `<tutorial-name>_files` folder. Figures and tables
from Tutorials 3 and 4 are displayed directly in their HTML reports rather than
exported as separate PNG, CSV, or Excel files.

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
  displayed figures, tables, settings, and R session information embedded.

Only configurations and simulation files are written separately because they
are required inputs to later tutorial steps. Evaluation and sensitivity figures
and tables exist only in their rendered HTML reports.

## Software

The manuscript results were generated with R 4.5.1, PK-Sim 12.2, MoBi 12.2, esqlabsR 5.6.0, and ospsuite 12.4.2. The scripts report the installed R package versions at run time and require esqlabsR 5.6.0 or later and ospsuite 12.4.2 or later. Newer versions can contain numerical or interface changes, so record the versions used for every reproduced analysis.
