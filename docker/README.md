# Running the tutorial with Docker

Docker packages the exact software this tutorial needs (R, Quarto, .NET 8 and the Open Systems
Pharmacology R packages at fixed versions) into one image. You do not need to install R, Quarto,
PK-Sim or MoBi. PK-Sim and MoBi are only needed to build or edit models; the `ospsuite` package in the
image contains the simulation engine.

The image holds only software. Your repository folder is mounted into the container at `/work`, so
reports and results are written back into your folder.

## What is in the image

| Component | Version |
|---|---|
| Ubuntu | 24.04 |
| R | 4.5.1 (conda-forge) |
| Quarto | 1.9.38 at the time of testing (latest on conda-forge when built) |
| .NET runtime | 8 |
| rSharp / ospsuite.utils / tlf / ospsuite.plots | 1.2.3 / 1.11.0 / 1.6.2 / 1.1.0 |
| ospsuite / esqlabsR | 12.4.2 / 5.6.0 |
| System library | libxml2 (required by the ospsuite simulation engine on Linux) |

These versions reproduce all 132 published fold errors of the a priori workflow exactly.

## Quick start

### Windows

1. Install and start **Docker Desktop** (wait for "Engine running").
2. Open **PowerShell** in the repository folder and run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File docker\pbpk.ps1 apriori
   ```
   The first run builds the image (15 to 30 minutes, about 1 GB download). Later runs start immediately.
3. Expected ending: `MATCH: all fold errors reproduce the published results.`
4. Then:
   ```powershell
   powershell -ExecutionPolicy Bypass -File docker\pbpk.ps1 summary
   ```

The same `powershell -ExecutionPolicy Bypass -File docker\pbpk.ps1 <command>` line also works from
Command Prompt.

### macOS (Intel and Apple Silicon) and Linux

1. Install and start **Docker Desktop** (wait for "Engine running").
   On Linux, [Docker Engine](https://docs.docker.com/engine/install/) without the Desktop GUI also works.
2. Open a terminal in the repository folder and run:
   ```bash
   bash docker/pbpk.sh apriori
   ```
   The first run builds the image (15 to 30 minutes, about 1 GB download). Later runs start immediately.
3. Expected ending: `MATCH: all fold errors reproduce the published results.`
4. Then:
   ```bash
   bash docker/pbpk.sh summary
   ```

**Apple Silicon note (M1 / M2 / M3 / M4):** the image is built for x86_64. Docker Desktop
uses Rosetta 2 to run it transparently. The `pbpk.sh` launcher passes `--platform linux/amd64`
automatically. Expect the first run to take slightly longer than on Intel hardware; results are
identical.

## Commands

| Command | What it does | Time |
|---|---|---|
| `apriori` | Stages 1, 2, 3 and 5; stops at the first failure; refuses to reuse an old simulation run; compares the fold errors with the committed table | ~6 min |
| `summary` | Within-2-fold counts by species and endpoint | seconds |
| `compare` | Comparison with the committed table only | seconds |
| `sensitivity` | Stage 4 (local sensitivity analysis) | ~15 min |
| `versions` | Software versions inside the image | seconds |
| `build` | Rebuild the image (launcher only) | 15 to 30 min |
| `help` | List of commands | seconds |

## Using Docker directly (any operating system)

If you prefer raw `docker` commands instead of the launchers:

```bash
# Build (all platforms — the --platform flag ensures x86_64 on Apple Silicon too)
docker build --platform linux/amd64 -t pbpk-mab-nam docker

# Run
docker run --rm --platform linux/amd64 -v "${PWD}:/work" pbpk-mab-nam apriori   # PowerShell
docker run --rm --platform linux/amd64 -v "%cd%:/work"  pbpk-mab-nam apriori   # Command Prompt
docker run --rm --platform linux/amd64 -v "$PWD:/work"  pbpk-mab-nam apriori   # macOS / Linux
```

## What a run changes

A run rewrites the configuration workbooks, the rendered `.html` reports, the tornado figure and table,
and `latest_simulation_run.txt`, and adds a new dated folder under
`02_APriori_PBPK_Workflow/SimsOutputs/SimulationResults/` plus logs in `_pbpk_logs/` (ignored by git).
To return to the committed state: `git checkout -- .` and delete the new dated folder.

## Limitations

- The image targets the a priori workflow (`02_APriori_PBPK_Workflow`). The study-design part
  (`03_Study_Simulations`) uses the same packages but simulates about 100,000 profiles and takes hours;
  it has not been run in this image.
- Results were verified with the package versions above. The bundled reports were produced on Windows
  with R 4.6.1, ospsuite 12.4.3 and esqlabsR 5.7.0; both setups give identical fold errors.
- `ospsuite` 13 is not supported by the scripts (Stage 2 fails), which is why versions are pinned.
- Building the image needs internet access to Ubuntu, conda-forge and GitHub.
- The image targets x86_64 (Intel/AMD). Apple Silicon Macs run it via Rosetta 2 emulation;
  pass `--platform linux/amd64` to `docker build` and `docker run` (the launchers do this
  automatically).

## Using it with an AI assistant

`skills/pbpk-apriori/SKILL.md` describes these commands and the rules from the repository
README ("Appropriate uses of an LLM") for AI coding assistants that read Agent Skills, so an assistant
runs the fixed runner instead of writing its own analysis code. Copy the `pbpk-apriori` folder into
the skills folder your assistant reads if it does not pick it up from this location.
