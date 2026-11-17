#!/usr/bin/env python3
"""
NAMLink PBPK mAb NAM Tutorial - MCP Server
===========================================

Exposes the a priori PBPK workflow and pre-computed study-design results of
the namlink-org/PBPK_mAb_NAM_Tutorial repository as tools callable by any AI
assistant that supports the Model Context Protocol (MCP).

Quickstart
----------
From the repository root:

    pip install -r mcp/requirements.txt
    python mcp/server.py

Or point the server at the repository from any directory:

    PBPK_REPO_PATH=/path/to/PBPK_mAb_NAM_Tutorial python mcp/server.py

See mcp/README.md for client configuration.
"""

import csv
import os
import platform
import re
import subprocess
import threading
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from mcp.server.mcpserver import MCPServer

# ---------------------------------------------------------------------------
# Repository root
# ---------------------------------------------------------------------------
# Resolved from the PBPK_REPO_PATH environment variable, falling back to the
# directory one level above this file (i.e. mcp/ → repo root).
_env_path = os.environ.get("PBPK_REPO_PATH")
REPO_ROOT = Path(_env_path).resolve() if _env_path else Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# MCP server instance
# ---------------------------------------------------------------------------
INSTRUCTIONS = (
    "Tools for the NAMLink PBPK mAb NAM Tutorial repository "
    "(namlink-org/PBPK_mAb_NAM_Tutorial). "
    "Run the a priori workflow, query fold errors and accuracy, "
    "look up study-design results, and inspect molecule details. "
    "Read results with get_fold_errors, get_accuracy_summary and query_study_design; "
    "call run_docker_command only when the user asks to run the workflow. "
    "Never re-run Stages 6-8; use query_study_design to read pre-computed results."
)

mcp = MCPServer("pbpk-namlink", instructions=INSTRUCTIONS, version="1.0.0")

# ---------------------------------------------------------------------------
# Authoritative molecule catalogue
# Verified against repo source code and CSV files.
# ---------------------------------------------------------------------------
_MOLECULES: dict[str, dict[str, Any]] = {
    "Adalimumab": {
        "target": "TNF-α",
        "igg_subclass": "Human IgG1",
        "species_tested": ["Monkey", "Human"],
        "study_design_coverage": False,
        "notes": [
            "Human dosing Route is 'IV Infusion' (no duration string). "
            "Stage 1 resolves this to 30 minutes via a molecule-specific rule "
            "in resolve_infusion_minutes() evaluated before the regex patterns. "
            "All other human mAbs must embed the infusion duration in the Route string.",
        ],
    },
    "Atezolizumab": {
        "target": "PD-L1",
        "igg_subclass": "Humanized IgG1 (Fc-aglyco, no effector function)",
        "species_tested": ["Monkey", "Human"],
        "study_design_coverage": False,
        "notes": [],
    },
    "Avelumab": {
        "target": "PD-L1",
        "igg_subclass": "Human IgG1",
        "species_tested": ["Monkey", "Human"],
        "study_design_coverage": False,
        "notes": [],
    },
    "Bevacizumab": {
        "target": "VEGF-A",
        "igg_subclass": "Humanized IgG1",
        "species_tested": ["Monkey", "Human"],
        "study_design_coverage": False,
        "notes": [],
    },
    "Golimumab": {
        "target": "TNF-α",
        "igg_subclass": "Human IgG1",
        "species_tested": ["Monkey", "Human"],
        "study_design_coverage": True,
        "notes": [
            "Used in study-design reanalysis (Stages 6-8) with the uncalibrated "
            "nominal a priori model.",
            "Two 3 mg/kg profiles produced no output after retry and were excluded "
            "only from those matched dose cells. All other doses for those monkeys "
            "remain in the analysis.",
        ],
    },
    "Nivolumab": {
        "target": "PD-1",
        "igg_subclass": "Human IgG4",
        "species_tested": ["Monkey", "Human"],
        "study_design_coverage": True,
        "notes": [
            "Used in study-design reanalysis (Stages 6-8) with a calibrated model: "
            "a priori Anti-PD1 structure with FcRn Kd set to 0.39 µmol/L. "
            "No uncalibrated Nivolumab arm is simulated.",
        ],
    },
    "Pembrolizumab": {
        "target": "PD-1",
        "igg_subclass": "Humanized IgG4",
        "species_tested": ["Monkey", "Human"],
        "study_design_coverage": False,
        "notes": [],
    },
    "Tocilizumab": {
        "target": "IL-6R",
        "igg_subclass": "Humanized IgG1",
        "species_tested": ["Monkey", "Human"],
        "study_design_coverage": False,
        "notes": [],
    },
}

_ALLOWED_COMMANDS = frozenset({"apriori", "sensitivity", "summary", "compare", "versions", "help"})

_COMMAND_DESCRIPTIONS = {
    "apriori": "Run Stages 1 → 2 → 3 → 5. Verifies fold errors against the published table. ~6 min.",
    "sensitivity": "Run Stage 4 (local one-way sensitivity of clearance). Requires Stages 1 and 2. 15-20 min.",
    "summary": "Print within-2-fold counts by species and endpoint. Seconds.",
    "compare": "Compare current fold-error table against the committed table. No re-simulation. Seconds.",
    "versions": "Report R, Quarto, rSharp, ospsuite, esqlabsR and .NET versions inside the image. Seconds.",
    "help": "List all available commands. Seconds.",
}

_SPECIES = ("Monkey", "Human")
_METRICS = ("AUC0-tlast", "Cmax", "Clearance")
_EVAL_STATUS = ("Evaluated", "Not evaluable")
_SD_MOLECULES = ("Golimumab", "Nivolumab")
_SD_DESIGNS = ("2 dose groups", "3 dose groups", "5 dose groups")
_SD_DOSES_BY_DESIGN = {"2 dose groups": (1.0, 10.0), "3 dose groups": (0.1, 1.0, 10.0),
                       "5 dose groups": (0.1, 1.0, 3.0, 10.0, 30.0)}
_SD_N_PER_GROUP = (2, 3, 6)
_SD_CV = (0.3, 0.6)
_SD_DOSES = (0.1, 1.0, 3.0, 10.0, 30.0)
_SD_ENDPOINTS = ("AUC0-28d", "Cmax", "Terminal clearance")

_FE_TABLE = "02_APriori_PBPK_Workflow/SimsOutputs/Tables/Supplement_Fold_Error_Tornado_Data.csv"
_SD_TABLES = "03_Study_Simulations/SimsOutputs/Step3_Results/Tables/"

# One Docker run at a time: two containers writing the same repository corrupt its outputs.
_RUN_LOCK = threading.Lock()


class InvalidArgument(ValueError):
    def __init__(self, field: str, value: Any, allowed: Any):
        self.payload = {
            "error": f"Invalid {field}: {value!r}.",
            "field": field,
            "allowed_values": list(allowed),
        }
        super().__init__(self.payload["error"])


def _choice(field: str, value: Optional[str], allowed: tuple[str, ...]) -> Optional[str]:
    """Match a text argument to its canonical value, ignoring case and surrounding spaces."""
    if value is None:
        return None
    key = re.sub(r"\s+", " ", str(value)).strip().lower()
    for option in allowed:
        if option.lower() == key:
            return option
    raise InvalidArgument(field, value, allowed)


def _number(field: str, value: Optional[float], allowed: tuple[float, ...], percent: bool = False) -> Optional[float]:
    if value is None:
        return None
    v = float(value)
    if percent and v > 1:
        v = v / 100.0
    for option in allowed:
        if abs(option - v) < 1e-9:
            return option
    raise InvalidArgument(field, value, allowed)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read_csv(repo_relative_path: str) -> list[dict[str, str]]:
    """Read a repository-relative CSV and return rows as a list of dicts."""
    path = REPO_ROOT / repo_relative_path
    if not path.is_file():
        raise FileNotFoundError(
            f"CSV not found at {repo_relative_path}. "
            "Ensure the repository is intact and the workflow has been run."
        )
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _to_float(value: str) -> Optional[float]:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _to_int(value: str) -> Optional[int]:
    f = _to_float(value)
    return int(f) if f is not None else None


def _launcher_args(command: str) -> list[str]:
    """Return the platform-appropriate launcher command."""
    if platform.system() == "Windows":
        return [
            "powershell", "-ExecutionPolicy", "Bypass", "-File",
            str(REPO_ROOT / "docker" / "pbpk.ps1"), command,
        ]
    return ["bash", str(REPO_ROOT / "docker" / "pbpk.sh"), command]


def _filter_rows(
    rows: list[dict[str, str]],
    **criteria: Any,
) -> list[dict[str, str]]:
    """
    Filter CSV rows by column value.  None criteria are skipped.
    Numeric comparisons use a small tolerance for floats.
    """
    out = []
    for row in rows:
        match = True
        for col, val in criteria.items():
            if val is None:
                continue
            cell = row.get(col, "")
            if isinstance(val, float):
                parsed = _to_float(cell)
                if parsed is None or abs(parsed - val) > 1e-9:
                    match = False
                    break
            elif isinstance(val, int):
                parsed = _to_float(cell)
                if parsed is None or int(round(parsed)) != val:
                    match = False
                    break
            else:
                if cell != str(val):
                    match = False
                    break
        if match:
            out.append(row)
    return out


# ---------------------------------------------------------------------------
# Tool: check_prerequisites
# ---------------------------------------------------------------------------

@mcp.tool()
def check_prerequisites() -> dict[str, Any]:
    """
    Verify that all prerequisites are satisfied before running the workflow.

    Checks performed
    ----------------
    1. The repository was cloned with git (not downloaded as a ZIP).
       The apriori and compare commands require git history.
    2. The checkout is v0.2.1 or later. The v0.2.0 file-name bug makes the
       Docker runner stop at startup; the detail names the current branch.
    3. All required input files are present on disk.
    4. Docker Engine is running and reachable on the system PATH.

    Returns
    -------
    all_passed : bool
    summary    : "N/M checks passed"
    checks     : list of {check, status ("PASS"|"FAIL"|"ERROR"), detail}
      detail is null on PASS and contains a remediation step on FAIL.
    """
    checks: list[dict[str, Any]] = []

    # ── 1. Git clone ──────────────────────────────────────────────────────────
    git_dir = REPO_ROOT / ".git"
    if git_dir.is_dir():
        checks.append({
            "check": "Repository is a git clone",
            "status": "PASS",
            "detail": None,
        })
    else:
        checks.append({
            "check": "Repository is a git clone",
            "status": "FAIL",
            "detail": (
                "The repository must be cloned with git, not downloaded as a ZIP. "
                "The apriori and compare commands require git history to verify results. "
                "Re-clone: git clone https://github.com/namlink-org/PBPK_mAb_NAM_Tutorial.git"
            ),
        })

    # ── 2. Checkout version (same rule as docker/run_pipeline.sh) ─────────────
    branch = None
    if git_dir.is_dir():
        try:
            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=REPO_ROOT, capture_output=True, text=True, timeout=10,
            ).stdout.strip() or None
        except (OSError, subprocess.SubprocessError):
            branch = None
    stage1 = REPO_ROOT / "02_APriori_PBPK_Workflow" / "Scripts" / "01_Setup_Configurations.qmd"
    try:
        old_bug = ("mAb_data_clean.csv" in stage1.read_text(encoding="utf-8", errors="replace")
                   and not (REPO_ROOT / "00_Data" / "Monkey" / "mAb_data_clean.csv").is_file())
        checks.append({
            "check": "Checkout is v0.2.1 or later",
            "status": "FAIL" if old_bug else "PASS",
            "detail": (
                f"This checkout (branch '{branch}') still has the v0.2.0 file-name bug, "
                "so the Docker runner will stop. Switch: git checkout main"
            ) if old_bug else None,
        })
    except OSError as exc:
        checks.append({"check": "Checkout is v0.2.1 or later", "status": "ERROR", "detail": str(exc)})

    # ── 3. Required input files ───────────────────────────────────────────────
    required_files = [
        ("00_Data/Monkey/mAb_data.csv",       "Monkey observed PK data"),
        ("00_Data/Human/mAb_data_human.csv",   "Human observed PK data"),
        ("00_Data/Monkey/Parameters.xlsx",     "Monkey mechanistic parameters"),
        ("00_Data/Human/Parameters_human.xlsx","Human mechanistic parameters"),
    ]
    for rel_path, description in required_files:
        present = (REPO_ROOT / rel_path).is_file()
        checks.append({
            "check": f"File present: {rel_path}",
            "status": "PASS" if present else "FAIL",
            "detail": None if present else f"Required file missing: {description}",
        })

    # ── 4. Docker ─────────────────────────────────────────────────────────────
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if result.returncode == 0:
            checks.append({
                "check": "Docker Engine is running",
                "status": "PASS",
                "detail": None,
            })
        else:
            checks.append({
                "check": "Docker Engine is running",
                "status": "FAIL",
                "detail": (
                    "Docker returned a non-zero exit code. "
                    "Start Docker Desktop and wait for 'Engine running' in the system tray."
                ),
            })
    except FileNotFoundError:
        checks.append({
            "check": "Docker Engine is running",
            "status": "FAIL",
            "detail": (
                "Docker was not found on PATH. "
                "Install Docker Desktop from https://www.docker.com/products/docker-desktop/"
            ),
        })
    except subprocess.TimeoutExpired:
        checks.append({
            "check": "Docker Engine is running",
            "status": "FAIL",
            "detail": (
                "docker info timed out. "
                "Docker Desktop may still be starting; wait 30 seconds and retry."
            ),
        })

    passed = sum(1 for c in checks if c["status"] == "PASS")
    return {
        "all_passed": passed == len(checks),
        "summary": f"{passed}/{len(checks)} checks passed",
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# Tool: run_docker_command
# ---------------------------------------------------------------------------

@mcp.tool()
def run_docker_command(command: str) -> dict[str, Any]:
    """
    Execute a pipeline command inside the containerised PBPK environment.

    This tool actually runs Docker. Call it only when the user explicitly asks
    to run the workflow. To read already-generated results, use get_fold_errors,
    get_accuracy_summary, or get_pipeline_status instead.

    Available commands
    ------------------
    apriori     Run Stages 1 → 2 → 3 → 5 in sequence. Stops at the first
                failure. Refuses to reuse an existing simulation run. Compares
                fold errors against the committed published table. ~6 min.
    sensitivity Run Stage 4: one-way local sensitivity analysis of clearance
                to target reference concentration, kint, and kdeg. Requires
                Stages 1 and 2 to have completed first. Stage 3 is not
                required. 15-20 min.
    summary     Print within-2-fold counts by species and endpoint from the
                current fold-error table. Seconds.
    compare     Compare the current fold-error table against the committed
                (published) table without re-simulating. Seconds.
    versions    Report R, Quarto, rSharp, ospsuite, esqlabsR and .NET
                versions inside the Docker image. Seconds.
    help        List all available commands. Seconds.

    Returns
    -------
    status          : "MATCH" | "DIFFERENT" | "STOPPED" | "OK" | "BUSY" | "ERROR"
    full_output     : complete stdout + stderr from the runner
    stopped_message : the STOPPED: line (present only when status is STOPPED)
    log_path        : path to the stage log file (present only when a stage failed)
    log_hint        : human-readable guidance for reading the log
    BUSY means another command is still running; only one runs at a time.
    """
    name = str(command).strip().lower()
    if name not in _ALLOWED_COMMANDS:
        return {
            "status": "ERROR",
            "error": f"Unknown command {command!r}.",
            "allowed_values": sorted(_ALLOWED_COMMANDS),
            "descriptions": _COMMAND_DESCRIPTIONS,
        }

    if not _RUN_LOCK.acquire(blocking=False):
        return {
            "status": "BUSY",
            "error": "Another pipeline command is still running. Wait for it to finish, then retry.",
        }
    try:
        proc = subprocess.run(
            _launcher_args(name),
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,   # 30-minute ceiling
        )
    except FileNotFoundError as exc:
        return {
            "status": "ERROR",
            "error": (
                f"Launcher not found: {exc}. "
                "Ensure Docker Desktop is installed and the repository is intact at "
                f"{REPO_ROOT}."
            ),
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "ERROR",
            "error": f"Command '{name}' exceeded the 30-minute time limit.",
        }
    finally:
        _RUN_LOCK.release()

    output = (proc.stdout or "") + (proc.stderr or "")

    # ── Parse outcome ─────────────────────────────────────────────────────────
    if "MATCH: all fold errors reproduce the published results." in output:
        return {"status": "MATCH", "full_output": output}

    if "DIFFERENT: see the rows above." in output:
        return {"status": "DIFFERENT", "full_output": output}

    for line in output.splitlines():
        if line.startswith("STOPPED:"):
            log_match = re.search(r"_pbpk_logs/\S+\.log", line)
            log_path = log_match.group() if log_match else None
            return {
                "status": "STOPPED",
                "stopped_message": line,
                "log_path": log_path,
                "log_hint": (
                    f"Read {log_path} for the full error trace. "
                    "The first 5 error lines are printed above the STOPPED line "
                    "in full_output."
                ) if log_path else None,
                "full_output": output,
            }

    if proc.returncode != 0:
        return {
            "status": "ERROR",
            "return_code": proc.returncode,
            "full_output": output,
        }

    return {"status": "OK", "full_output": output}


# ---------------------------------------------------------------------------
# Tool: get_pipeline_status
# ---------------------------------------------------------------------------

@mcp.tool()
def get_pipeline_status() -> dict[str, Any]:
    """
    Report the current state of the a priori workflow in this repository clone.

    Reads on-disk files only - does not execute Docker. Use this to determine
    whether the workflow has been run and what results are available before
    deciding whether to call run_docker_command.

    Returns
    -------
    repo_root               : resolved path to the repository root
    latest_run_folder       : value in latest_simulation_run.txt, or null
    fold_error_table_present: whether Supplement_Fold_Error_Tornado_Data.csv exists
    fold_error_row_count    : total rows in the fold-error table
    evaluated_count         : rows with Evaluation_status == "Evaluated"
    within_2fold_count      : evaluated rows with 0.5 ≤ fold_error ≤ 2.0
    sensitivity_report_present : whether Stage 4 HTML output exists
    note                    : guidance on interpreting the status
    """
    status: dict[str, Any] = {"repo_root": str(REPO_ROOT)}

    # Latest simulation run pointer
    run_txt = (
        REPO_ROOT
        / "02_APriori_PBPK_Workflow"
        / "SimsOutputs"
        / "latest_simulation_run.txt"
    )
    if run_txt.is_file():
        content = run_txt.read_text(encoding="utf-8").strip()
        status["latest_run_folder"] = content or None
    else:
        status["latest_run_folder"] = None

    # Fold-error table
    fe_csv = (
        REPO_ROOT
        / "02_APriori_PBPK_Workflow"
        / "SimsOutputs"
        / "Tables"
        / "Supplement_Fold_Error_Tornado_Data.csv"
    )
    if fe_csv.is_file():
        with open(fe_csv, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        evaluated = [r for r in rows if r.get("Evaluation_status") == "Evaluated"]
        within = [
            r for r in evaluated
            if (fe := _to_float(r.get("Fold_error", ""))) is not None
            and 0.5 <= fe <= 2.0
        ]
        status.update({
            "fold_error_table_present": True,
            "fold_error_row_count": len(rows),
            "evaluated_count": len(evaluated),
            "within_2fold_count": len(within),
        })
    else:
        status.update({
            "fold_error_table_present": False,
            "fold_error_row_count": 0,
            "evaluated_count": 0,
            "within_2fold_count": 0,
        })

    # Sensitivity analysis output
    sens_html = (
        REPO_ROOT
        / "02_APriori_PBPK_Workflow"
        / "Scripts"
        / "04_LocalSensitivityAnalysis.html"
    )
    status["sensitivity_report_present"] = sens_html.is_file()
    status["note"] = (
        "Call run_docker_command('compare') for a definitive MATCH/DIFFERENT verdict. "
        "The published table has 132 rows (109 evaluated, 96 within 2-fold); "
        "MATCH means all 132 fold-error values reproduce it."
    )

    return status


# ---------------------------------------------------------------------------
# Tool: get_fold_errors
# ---------------------------------------------------------------------------

@mcp.tool()
def get_fold_errors(
    species: Optional[str] = None,
    metric: Optional[str] = None,
    molecule: Optional[str] = None,
    evaluation_status: Optional[str] = None,
) -> dict[str, Any]:
    """
    Query the a priori fold-error table produced by Stage 3.

    Reads the committed CSV directly - does not re-run simulations.
    Fold error is defined as Predicted / Observed. The within-2-fold range
    is 0.5-2.0 (inclusive).

    Parameters
    ----------
    species           : "Monkey" or "Human". Omit for both.
    metric            : "AUC0-tlast", "Cmax", or "Clearance". Omit for all.
    molecule          : e.g. "Tocilizumab", "Nivolumab". Omit for all.
    evaluation_status : "Evaluated" or "Not evaluable". Omit for all.
                        Clearance rows with >20 % AUCinf extrapolation are
                        marked "Not evaluable" and excluded from fold-error
                        counts and the MATCH check.

    Returns
    -------
    rows                   : filtered fold-error rows (numeric types)
    total_rows             : count after filtering
    evaluated_count        : rows with Evaluation_status == "Evaluated"
    within_2fold_count     : evaluated rows with 0.5 ≤ fold_error ≤ 2.0
    within_2fold_fraction  : within_2fold_count / evaluated_count
    fold_error_definition  : "Predicted / Observed"

    Text filters ignore case. An unknown value returns an error with the
    allowed values instead of an empty result.
    """
    try:
        raw = _read_csv(_FE_TABLE)
    except FileNotFoundError as exc:
        return {
            "error": str(exc),
            "hint": "Run run_docker_command('apriori') to generate the fold-error table.",
        }
    try:
        species = _choice("species", species, _SPECIES)
        metric = _choice("metric", metric, _METRICS)
        # Molecules present in the table, so antibodies added to the data are accepted too.
        molecule = _choice("molecule", molecule, tuple(sorted({r["Molecule"] for r in raw})))
        evaluation_status = _choice("evaluation_status", evaluation_status, _EVAL_STATUS)
    except InvalidArgument as exc:
        return exc.payload

    filtered = _filter_rows(
        raw,
        Species=species,
        Metric=metric,
        Molecule=molecule,
        Evaluation_status=evaluation_status,
    )

    rows = [
        {
            "species": r["Species"],
            "metric": r["Metric"],
            "molecule": r["Molecule"],
            "dose_mg_kg": _to_float(r["Dose_mg_kg"]),
            "fold_error": _to_float(r["Fold_error"]),
            "log2_fold_error": _to_float(r["Log2_fold_error"]),
            "evaluation_status": r["Evaluation_status"],
        }
        for r in filtered
    ]

    evaluated = [r for r in rows if r["evaluation_status"] == "Evaluated"]
    within = [
        r for r in evaluated
        if r["fold_error"] is not None and 0.5 <= r["fold_error"] <= 2.0
    ]

    return {
        "rows": rows,
        "total_rows": len(rows),
        "evaluated_count": len(evaluated),
        "within_2fold_count": len(within),
        "within_2fold_fraction": round(len(within) / len(evaluated), 4) if evaluated else None,
        "fold_error_definition": "Predicted / Observed (within-2-fold range: 0.5-2.0 inclusive)",
    }


# ---------------------------------------------------------------------------
# Tool: get_accuracy_summary
# ---------------------------------------------------------------------------

@mcp.tool()
def get_accuracy_summary() -> dict[str, Any]:
    """
    Return the within-2-fold accuracy summary broken down by species and endpoint.

    Reads the committed fold-error table - does not re-run simulations.
    Mirrors the output of the Docker 'summary' command in structured form,
    suitable for reporting in a scientific context.

    Returns
    -------
    by_species_endpoint : list of {species, metric, n_evaluated,
                          n_within_2fold, fraction_within_2fold, percent_within_2fold}
    overall             : {n_evaluated, n_within_2fold, fraction_within_2fold}
    published_benchmark : "MATCH on all 132 evaluated scenario-endpoints"
    interpretation_note : guidance on what the fold-error criterion means
    """
    try:
        raw = _read_csv(_FE_TABLE)
    except FileNotFoundError as exc:
        return {
            "error": str(exc),
            "hint": "Run run_docker_command('apriori') to generate the fold-error table.",
        }

    bucket: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in raw:
        if r.get("Evaluation_status") != "Evaluated":
            continue
        fe = _to_float(r.get("Fold_error", ""))
        if fe is not None:
            bucket[(r["Species"], r["Metric"])].append(fe)

    summary = []
    total_eval = 0
    total_within = 0
    for (species, metric), fold_errors in sorted(bucket.items()):
        n = len(fold_errors)
        w = sum(1 for fe in fold_errors if 0.5 <= fe <= 2.0)
        total_eval += n
        total_within += w
        summary.append({
            "species": species,
            "metric": metric,
            "n_evaluated": n,
            "n_within_2fold": w,
            "fraction_within_2fold": round(w / n, 4) if n else None,
            "percent_within_2fold": round(100 * w / n, 1) if n else None,
        })

    return {
        "by_species_endpoint": summary,
        "overall": {
            "n_evaluated": total_eval,
            "n_within_2fold": total_within,
            "fraction_within_2fold": round(total_within / total_eval, 4) if total_eval else None,
        },
        "published_benchmark": (
            "132 total rows; 109 Evaluated, 23 Not evaluable (Clearance with >20% AUCinf extrapolation). "
            "Of the 109 evaluated, 96 (88%) are within 2-fold. "
            "MATCH means the current run reproduced all 132 fold-error values exactly "
            "against the committed published table - not that all 132 are within 2-fold."
        ),
        "interpretation_note": (
            "Fold error = Predicted / Observed. Within-2-fold range: 0.5-2.0. "
            "Clearance rows with >20 % AUCinf extrapolation are excluded from counts "
            "(marked 'Not evaluable' in the fold-error table)."
        ),
    }


# ---------------------------------------------------------------------------
# Tool: query_study_design
# ---------------------------------------------------------------------------

@mcp.tool()
def query_study_design(
    molecule: str,
    design: Optional[str] = None,
    n_per_group: Optional[int] = None,
    variability_cv: Optional[float] = None,
    dose_mg_kg: Optional[float] = None,
    endpoint: Optional[str] = None,
) -> dict[str, Any]:
    """
    Query pre-computed monkey PK study-design performance results (Stages 6-8).

    IMPORTANT: Never re-run Stages 6-8. This tool reads pre-computed, committed
    CSVs directly. Stage 7 takes several hours and is not available as a Docker
    command.

    Coverage
    --------
    Molecules  : Golimumab (uncalibrated a priori) and Nivolumab
                 (FcRn Kd calibrated to 0.39 µmol/L)
    Doses      : 0.1, 1, 3, 10, 30 mg/kg
    Designs    : "2 dose groups", "3 dose groups", "5 dose groups"
                 ({1,10}; {0.1,1,10}; all five doses respectively)
    Animals    : 2, 3, or 6 per group (n_per_group)
    Variability: 0.3 (30 % CV) or 0.6 (60 % CV) on five shared mechanistic inputs
    Endpoints  : "AUC0-28d", "Cmax", "Terminal clearance"

    Parameters
    ----------
    molecule      : "Golimumab" or "Nivolumab" (required)
    design        : "2 dose groups", "3 dose groups", or "5 dose groups"
    n_per_group   : 2, 3, or 6
    variability_cv: 0.3 or 0.6 (30 and 60 are read as percent)
    dose_mg_kg    : 0.1, 1.0, 3.0, 10.0, or 30.0
    endpoint      : "AUC0-28d", "Cmax", or "Terminal clearance"
    Text values ignore case; an unknown value returns the allowed values.

    Returns
    -------
    overall_success  : overall fraction within 2-fold by design
    by_endpoint      : performance broken down by endpoint
    fold_error_detail: dose-level statistics (only when dose_mg_kg or endpoint given)
    important_note   : caveat on the conditional nature of the results
    """
    try:
        molecule = _choice("molecule", molecule, _SD_MOLECULES)
        design = _choice("design", design, _SD_DESIGNS)
        endpoint = _choice("endpoint", endpoint, _SD_ENDPOINTS)
        n = _number("n_per_group", n_per_group, tuple(float(x) for x in _SD_N_PER_GROUP))
        n_per_group = int(n) if n is not None else None
        variability_cv = _number("variability_cv", variability_cv, _SD_CV, percent=True)
        dose_mg_kg = _number("dose_mg_kg", dose_mg_kg, _SD_DOSES)
    except InvalidArgument as exc:
        if exc.payload["field"] == "molecule":
            exc.payload["note"] = "The study-design reanalysis (Stages 6-8) covers only Golimumab and Nivolumab."
        return exc.payload

    result: dict[str, Any] = {}
    file_errors: list[str] = []

    # ── Overall success ───────────────────────────────────────────────────────
    try:
        raw = _read_csv(_SD_TABLES + "study_design_overall_success.csv")
        filtered = _filter_rows(
            raw,
            Molecule=molecule,
            Design=design,
            N_per_group=n_per_group,
            Variability_CV=variability_cv,
        )
        result["overall_success"] = [
            {
                "molecule": r["Molecule"],
                "variability_cv": _to_float(r["Variability_CV"]),
                "design": r["Design"],
                "n_per_group": _to_int(r["N_per_group"]),
                "total_animals": _to_int(r["Total_animals"]),
                "replicates": _to_int(r["Replicates"]),
                "fraction_within_2fold": _to_float(r["Fraction_within_2fold"]),
            }
            for r in filtered
        ]
    except FileNotFoundError as exc:
        file_errors.append(str(exc))

    # ── By endpoint ───────────────────────────────────────────────────────────
    try:
        raw = _read_csv(_SD_TABLES + "study_design_endpoint_success.csv")
        filtered = _filter_rows(
            raw,
            Molecule=molecule,
            Design=design,
            N_per_group=n_per_group,
            Variability_CV=variability_cv,
            Endpoint=endpoint,
        )
        result["by_endpoint"] = [
            {
                "molecule": r["Molecule"],
                "variability_cv": _to_float(r["Variability_CV"]),
                "design": r["Design"],
                "n_per_group": _to_int(r["N_per_group"]),
                "endpoint": r["Endpoint"],
                "fraction_within_2fold": _to_float(r["Fraction_within_2fold"]),
            }
            for r in filtered
        ]
    except FileNotFoundError as exc:
        file_errors.append(str(exc))

    # ── Fold-error detail by dose (only when filtering is narrow enough) ──────
    if dose_mg_kg is not None or endpoint is not None:
        try:
            raw = _read_csv(_SD_TABLES + "study_design_fold_error_summary.csv")
            filtered = _filter_rows(
                raw,
                Molecule=molecule,
                Design=design,
                N_per_group=n_per_group,
                Variability_CV=variability_cv,
                Dose_mg_kg=dose_mg_kg,
                Endpoint=endpoint,
            )
            result["fold_error_detail"] = [
                {
                    "molecule": r["Molecule"],
                    "variability_cv": _to_float(r["Variability_CV"]),
                    "design": r["Design"],
                    "n_per_group": _to_int(r["N_per_group"]),
                    "dose_mg_kg": _to_float(r["Dose_mg_kg"]),
                    "endpoint": r["Endpoint"],
                    "fraction_within_2fold": _to_float(r["Fraction_within_2fold"]),
                    "mean_fold_error": _to_float(r["Mean_fold_error"]),
                    "geometric_mean_fold_error": _to_float(r["Geometric_mean_fold_error"]),
                    "relative_bias_percent": _to_float(r["Relative_bias_percent"]),
                    "rmse_percent": _to_float(r["RMSE_percent"]),
                    "median_fold_error": _to_float(r["Median_fold_error"]),
                    "fold_error_5th_pct": _to_float(r["Fold_error_5th_percentile"]),
                    "fold_error_95th_pct": _to_float(r["Fold_error_95th_percentile"]),
                }
                for r in filtered
            ]
        except FileNotFoundError as exc:
            file_errors.append(str(exc))
        if design and dose_mg_kg is not None and dose_mg_kg not in _SD_DOSES_BY_DESIGN[design]:
            result["note"] = (
                f"{dose_mg_kg:g} mg/kg is not part of the '{design}' design, so there is no "
                f"dose-level detail. Its doses are {', '.join(f'{d:g}' for d in _SD_DOSES_BY_DESIGN[design])} mg/kg."
            )

    # ── Caveats ───────────────────────────────────────────────────────────────
    if molecule == "Golimumab":
        model_note = "uncalibrated nominal a priori model"
    else:
        model_note = "calibrated model (FcRn Kd = 0.39 µmol/L)"

    result["important_note"] = (
        f"Results are conditional on the {molecule} {model_note}, "
        "the configured variability assumptions (30 % or 60 % CV on five shared "
        "mechanistic inputs: FcRn Kd, drug-target Kd, koff, kint, kdeg), "
        "and the 0.5-2.0 fold-error threshold used as a tutorial criterion - "
        "not a universal regulatory design standard."
    )

    if file_errors:
        result["file_errors"] = file_errors

    return result


# ---------------------------------------------------------------------------
# Tool: get_molecule_info
# ---------------------------------------------------------------------------

@mcp.tool()
def get_molecule_info(molecule: Optional[str] = None) -> dict[str, Any]:
    """
    Return pharmacological and repository-specific details for the reference mAbs.

    Parameters
    ----------
    molecule : Antibody name (e.g. "Tocilizumab", "Nivolumab"). Case is ignored.
               Omit to return all 8 molecules.

    Returns
    -------
    For each molecule:
      target               : pharmacological target
      igg_subclass         : IgG subclass and engineering notes
      species_tested       : ["Monkey", "Human"]
      study_design_coverage: whether included in Stages 6-8 study-design results
      notes                : list of repository-specific notes (Route rules,
                             calibration details, exclusion events)
    """
    if molecule is not None:
        try:
            name = _choice("molecule", molecule, tuple(sorted(_MOLECULES)))
        except InvalidArgument:
            key = str(molecule).strip().lower()
            candidates = [m for m in _MOLECULES if key and key in m.lower()]
            return {
                "error": (
                    f"No reference information for {str(molecule)[:80]!r}. Reference "
                    "information covers the eight published antibodies only. For an "
                    "antibody you added to the data, use get_fold_errors(molecule=...)."
                ),
                "available_molecules": sorted(_MOLECULES),
                "did_you_mean": candidates or None,
            }
        return {"molecule": name, **_MOLECULES[name]}

    return {
        "molecules": [
            {"molecule": name, **info}
            for name, info in sorted(_MOLECULES.items())
        ],
        "count": len(_MOLECULES),
        "study_design_molecules": ["Golimumab", "Nivolumab"],
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
