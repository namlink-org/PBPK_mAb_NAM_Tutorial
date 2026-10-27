# Docker environment

The `docker/` folder provides a containerised environment for the a priori PBPK workflow
(`02_APriori_PBPK_Workflow`, Stages 1–3 and 5). The image bundles R, Quarto, .NET 8 and
the Open Systems Pharmacology R packages at fixed versions, eliminating the need for a
manual software installation. The repository itself is mounted into the container at
`/work` at runtime; all reports and results are written back to the host folder.

PK-Sim and MoBi are not included. The `ospsuite` package bundles the simulation engine,
which is sufficient to run the a priori workflow.

## Software versions

| Component | Version |
|---|---|
| Ubuntu | 24.04 |
| R | 4.5.1 (conda-forge) |
| Quarto | latest on conda-forge at build time (1.9.38 when tested) |
| .NET runtime | 8 |
| rSharp / ospsuite.utils / tlf / ospsuite.plots | 1.2.3 / 1.11.0 / 1.6.2 / 1.1.0 |
| ospsuite / esqlabsR | 12.4.2 / 5.6.0 |
| libxml2 | system package (required by the ospsuite simulation engine on Linux) |

These versions reproduce all 132 published fold errors of the a priori workflow exactly.
The bundled reports were produced on Windows with R 4.6.1, ospsuite 12.4.3 and
esqlabsR 5.7.0; both configurations produce identical fold errors.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
  On Linux, [Docker Engine](https://docs.docker.com/engine/install/) without the Desktop
  GUI is also supported.
- The repository cloned locally (not downloaded as a ZIP; the `compare` and `apriori`
  commands require git history to verify results).
- All commands are run from the **repository root**.

## Quick start

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File docker\pbpk.ps1 apriori
```

The same command works from Command Prompt. The first execution builds the image
(15–30 minutes, approximately 1 GB download); subsequent runs start immediately.

A successful run ends with:

```
MATCH: all fold errors reproduce the published results.
```

### macOS and Linux

```bash
bash docker/pbpk.sh apriori
```

The first execution builds the image (15–30 minutes, approximately 1 GB download);
subsequent runs start immediately.

A successful run ends with:

```
MATCH: all fold errors reproduce the published results.
```

**Apple Silicon (M1 / M2 / M3 / M4):** the image targets x86_64. Docker Desktop runs it
via Rosetta 2 emulation. The `pbpk.sh` launcher passes `--platform linux/amd64`
automatically; no additional configuration is required. Build time on Apple Silicon is
longer than on Intel hardware; numerical results are identical.

## Available commands

| Command | Description | Approximate time |
|---|---|---|
| `apriori` | Runs Stages 1, 2, 3 and 5 of the a priori workflow in sequence; stops at the first failure; refuses to reuse an existing simulation run; compares the resulting fold-error table against the committed (published) table. Stages 4, 6, 7 and 8 are not included. | 6 min |
| `summary` | Prints within-2-fold counts by species and endpoint from the current fold-error table | seconds |
| `compare` | Compares the current fold-error table against the committed table without re-running simulations | seconds |
| `sensitivity` | Runs Stage 4 (local sensitivity analysis) | 15 min |
| `versions` | Prints R, Quarto, rSharp, ospsuite, esqlabsR and .NET versions inside the image | seconds |
| `build` | Rebuilds the image explicitly (the launchers rebuild automatically when no image is found) | 15–30 min |
| `help` | Lists available commands | seconds |

## Docker Compose

A `docker-compose.yml` is provided at the repository root. It defines the same image and
volume configuration as the launchers and follows the standard `docker compose run` pattern:

```bash
docker compose run --rm pbpk apriori     # run the a priori workflow
docker compose run --rm pbpk summary     # accuracy summary
docker compose run --rm pbpk help        # list all commands
docker compose build                     # build the image without running
```

This is equivalent to the launcher scripts and is the preferred entry point for users
already familiar with Docker Compose.

## Direct Docker invocation

The launchers (`pbpk.ps1` on Windows, `pbpk.sh` on macOS/Linux) and `docker-compose.yml`
are convenience wrappers. The equivalent raw Docker commands are:

```bash
# Build
docker build --platform linux/amd64 -t pbpk-mab-nam docker

# Run (substitute the appropriate working-directory variable for the shell in use)
docker run --rm --platform linux/amd64 -v "${PWD}:/work" pbpk-mab-nam apriori   # PowerShell
docker run --rm --platform linux/amd64 -v "%cd%:/work"  pbpk-mab-nam apriori   # Command Prompt
docker run --rm --platform linux/amd64 -v "$PWD:/work"  pbpk-mab-nam apriori   # macOS / Linux
```

## Files modified by a run

An `apriori` run rewrites the following tracked files:

- `02_APriori_PBPK_Workflow/Configurations/` — three configuration workbooks
- `02_APriori_PBPK_Workflow/Scripts/03_Process_Sims_Outputs.html` — main evaluation report
- `02_APriori_PBPK_Workflow/SimsOutputs/Figures/` — tornado figure
- `02_APriori_PBPK_Workflow/SimsOutputs/Tables/` — fold-error table
- `02_APriori_PBPK_Workflow/SimsOutputs/latest_simulation_run.txt` — pointer to the active run

It also creates a new timestamped folder under
`02_APriori_PBPK_Workflow/SimsOutputs/SimulationResults/` and writes logs to `_pbpk_logs/`
(excluded from version control). To restore the repository to its committed state:

```bash
git checkout -- .
# Then delete the timestamped folder created under SimsOutputs/SimulationResults/
```

## Limitations

- The image covers the a priori workflow only (Stages 1–5). Stages 6, 7 and 8
  (`03_Study_Simulations`) use the same packages but simulate approximately 100,000 profiles
  and take several hours; they have not been validated in this environment and are not
  available as Docker commands.
- `ospsuite` 13 is incompatible with the current scripts (Stage 2 fails with a locked-
  environment error); package versions are therefore pinned.
- Building the image requires internet access to the Ubuntu package repository,
  conda-forge and GitHub.
- The image targets x86_64. Apple Silicon is supported via Rosetta 2 emulation (see above).

## AI assistant integration

`skills/pbpk-apriori/SKILL.md` provides a machine-readable description of the available
commands and the rules governing their use, formatted for AI coding assistants that support
agent skills. An assistant configured with this skill will invoke the Docker runner rather
than generating its own simulation code. See [`skills/pbpk-apriori/README.md`](../skills/pbpk-apriori/README.md)
for integration instructions.
