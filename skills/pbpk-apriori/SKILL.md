---
name: pbpk-apriori
description: Run, reproduce and explain the a priori PBPK monoclonal-antibody workflow of this repository (Stages 1, 2, 3 and 5, optional Stage 4) inside the pinned Docker environment, verify the fold errors against the published table, and summarise accuracy. Use when asked to run, reproduce, verify or check the tutorial, re-run the simulations, or report how accurate the predictions are.
---

# PBPK mAb a priori workflow

This skill drives a fixed, tested runner. Do not write new simulation or analysis code: the
runner is what makes results reproducible.

## Rules (from the repository README, "Appropriate uses of an LLM")
- Never invent, estimate or change biological parameters, doses or observed data.
- Never edit files under `00_Data/`, `01_Models/` or the `.qmd` scripts unless the user explicitly
  asks for that specific change.
- Never choose or change model structure.
- Report a run as successful only if the runner prints `MATCH` (for `apriori`) or finishes without
  `STOPPED` (other commands). Otherwise quote the `STOPPED` line and the log file it names.
- Do not send confidential or proprietary molecule information to any service the user has not approved.

## Prerequisites
- Docker Desktop installed and running ("Engine running").
- Run commands from the repository root.

## Commands

On Windows (works from PowerShell, Command Prompt or Git Bash):
```
powershell -ExecutionPolicy Bypass -File docker/pbpk.ps1 <command>
```
On macOS or Linux:
```
docker build -t pbpk-mab-nam docker            # once
docker run --rm -v "$PWD:/work" pbpk-mab-nam <command>
```

| Command | What it does | Time |
|---|---|---|
| `versions` | Prints R, Quarto, rSharp, ospsuite, esqlabsR and .NET versions | seconds |
| `apriori` | Stages 1, 2, 3, 5; stops at the first failure; refuses to reuse an old simulation run; compares the new fold-error table with the committed one | about 6 min |
| `summary` | Within-2-fold counts by species and endpoint from the current table | seconds |
| `compare` | Only the comparison with the committed table | seconds |
| `sensitivity` | Stage 4, local sensitivity analysis | about 15 min |
| `build` | (Windows launcher only) rebuilds the image | 15 to 30 min the first time |

The first Windows run builds the image automatically if it does not exist.

## Workflow
1. Run `versions` to confirm the environment.
2. Run `apriori`. Wait for it to finish; do not interrupt.
3. If it prints `MATCH`, run `summary` and report the table.
4. If it prints `DIFFERENT` or `STOPPED`, report exactly what it printed and the log path under
   `_pbpk_logs/`. Do not try to "fix" scientific inputs.
5. Tell the user where outputs are:
   - Main report: `02_APriori_PBPK_Workflow/Scripts/03_Process_Sims_Outputs.html`
   - New simulation run: the folder named in `02_APriori_PBPK_Workflow/SimsOutputs/latest_simulation_run.txt`
   - Fold-error table: `02_APriori_PBPK_Workflow/SimsOutputs/Tables/Supplement_Fold_Error_Tornado_Data.csv`
6. Remind the user that the run modified tracked files (configuration workbooks, reports, the
   tornado figure) and created a new dated simulation folder. To discard: `git checkout -- .` and
   delete the new folder under `02_APriori_PBPK_Workflow/SimsOutputs/SimulationResults/`.

## Interpreting results
- Fold error = predicted / observed. Within 0.5 to 2 counts as "within 2-fold".
- Clearance is evaluable only when the observed data allow a reliable terminal phase
  (extrapolated AUC fraction at most 20%), so fewer clearance rows are evaluated.
- The predictions are a priori: observed data are used only for evaluation, never for fitting.

## Out of scope for this skill
- Adding a new antibody or target, and the `03_Study_Simulations` (study design) part.
