#!/usr/bin/env python3
"""
Local test script for the NAMLink MCP server tools.

Run from the repository root:
    python mcp/test_tools.py

Tests all 7 tools directly (bypassing the MCP protocol) so you can
verify the logic before connecting an MCP client.

run_docker_command is tested with 'versions' and 'help' only (seconds,
no simulation). Pass --full to also run 'apriori' (~6 min).
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Force UTF-8 output on Windows so box-drawing chars in messages don't crash
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Point the server at this repo
os.environ.setdefault("PBPK_REPO_PATH", str(Path(__file__).resolve().parent.parent))

# Import tools directly from server (bypasses MCP protocol)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from server import (
    check_prerequisites,
    get_accuracy_summary,
    get_fold_errors,
    get_molecule_info,
    get_pipeline_status,
    query_study_design,
    run_docker_command,
)

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
INFO = "\033[94mINFO\033[0m"


def pp(obj: object) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def section(title: str) -> None:
    print(f"\n{'-' * 60}")
    print(f"  {title}")
    print(f"{'-' * 60}")


def ok(msg: str) -> None:
    print(f"  [{PASS}] {msg}")


def fail(msg: str) -> None:
    print(f"  [{FAIL}] {msg}")
    sys.exit(1)


def info(msg: str) -> None:
    print(f"  [{INFO}] {msg}")


# ── 1. check_prerequisites ────────────────────────────────────────────────────

def test_check_prerequisites() -> None:
    section("1. check_prerequisites")
    result = check_prerequisites()
    pp(result)
    assert "all_passed" in result, "Missing all_passed key"
    assert "checks" in result and isinstance(result["checks"], list)
    for c in result["checks"]:
        status = c["status"]
        label  = c["check"]
        if status == "PASS":
            ok(label)
        elif status == "FAIL":
            info(f"FAIL (expected if Docker not running): {label} - {c['detail']}")
        else:
            info(f"ERROR: {label} - {c['detail']}")
    ok("check_prerequisites returned a structured result")


# ── 2. get_pipeline_status ────────────────────────────────────────────────────

def test_get_pipeline_status() -> None:
    section("2. get_pipeline_status")
    result = get_pipeline_status()
    pp(result)
    assert "fold_error_table_present" in result
    assert "evaluated_count" in result
    if result["fold_error_table_present"]:
        ok(f"Fold-error table present - {result['fold_error_row_count']} rows, "
           f"{result['evaluated_count']} evaluated, "
           f"{result['within_2fold_count']} within 2-fold")
    else:
        info("Fold-error table not yet generated (run apriori first)")
    ok("get_pipeline_status returned a structured result")


# ── 3. get_fold_errors ────────────────────────────────────────────────────────

def test_get_fold_errors() -> None:
    section("3. get_fold_errors")

    # 3a. All rows
    result = get_fold_errors()
    if "error" in result:
        info(f"Fold-error table not available: {result['error']}")
        return
    assert result["total_rows"] == 132, \
        f"Expected 132 total rows, got {result['total_rows']}"
    assert result["evaluated_count"] == 109, \
        f"Expected 109 evaluated, got {result['evaluated_count']}"
    assert result["within_2fold_count"] == 96, \
        f"Expected 96 within 2-fold, got {result['within_2fold_count']}"
    ok(f"All rows: total={result['total_rows']}, "
       f"evaluated={result['evaluated_count']}, "
       f"within_2fold={result['within_2fold_count']}")

    # 3b. Filter: Human Clearance
    result = get_fold_errors(species="Human", metric="Clearance")
    assert result["evaluated_count"] == 15, \
        f"Expected 15 Human Clearance evaluated, got {result['evaluated_count']}"
    ok(f"Human Clearance: {result['evaluated_count']} evaluated, "
       f"{result['within_2fold_count']} within 2-fold")

    # 3c. Filter: Tocilizumab
    result = get_fold_errors(molecule="Tocilizumab")
    assert result["total_rows"] > 0, "Expected rows for Tocilizumab"
    ok(f"Tocilizumab: {result['total_rows']} rows")

    # 3d. Invalid molecule - structured error listing the allowed values, not an empty table
    result = get_fold_errors(molecule="NotAMolecule")
    assert result.get("field") == "molecule" and "Tocilizumab" in result["allowed_values"], result
    ok("Unknown molecule returns the allowed values (no silent empty result)")


# ── 4. get_accuracy_summary ───────────────────────────────────────────────────

def test_get_accuracy_summary() -> None:
    section("4. get_accuracy_summary")
    result = get_accuracy_summary()
    if "error" in result:
        info(f"Fold-error table not available: {result['error']}")
        return
    pp(result)
    assert "by_species_endpoint" in result
    assert "overall" in result
    overall = result["overall"]
    assert overall["n_evaluated"] == 109, \
        f"Expected 109 evaluated, got {overall['n_evaluated']}"
    assert overall["n_within_2fold"] == 96, \
        f"Expected 96 within 2-fold, got {overall['n_within_2fold']}"
    ok(f"Overall: {overall['n_evaluated']} evaluated, "
       f"{overall['n_within_2fold']} within 2-fold "
       f"({100 * overall['fraction_within_2fold']:.1f} %)")


# ── 5. query_study_design ─────────────────────────────────────────────────────

def test_query_study_design() -> None:
    section("5. query_study_design")

    # 5a. All Golimumab designs
    result = query_study_design(molecule="Golimumab")
    if "file_errors" in result:
        fail(f"CSV read error: {result['file_errors']}")
    assert "overall_success" in result
    rows = result["overall_success"]
    assert len(rows) > 0, "Expected rows for Golimumab"
    ok(f"Golimumab - {len(rows)} overall-success rows returned")

    # 5b. Filtered: Nivolumab, 3 dose groups, N=3, 30% CV
    result = query_study_design(
        molecule="Nivolumab",
        design="3 dose groups",
        n_per_group=3,
        variability_cv=0.3,
    )
    rows = result.get("overall_success", [])
    assert len(rows) == 1, f"Expected 1 row for this filter, got {len(rows)}"
    frac = rows[0]["fraction_within_2fold"]
    ok(f"Nivolumab 3-group N=3 30%CV -> fraction_within_2fold = {frac}")

    # 5c. Dose-level detail
    result = query_study_design(
        molecule="Golimumab",
        dose_mg_kg=10.0,
        endpoint="AUC0-28d",
    )
    detail = result.get("fold_error_detail", [])
    assert len(detail) > 0, "Expected fold_error_detail when dose_mg_kg specified"
    ok(f"Golimumab dose=10 mg/kg AUC0-28d -> {len(detail)} fold_error_detail rows")

    # 5d. Invalid molecule
    result = query_study_design(molecule="Pembrolizumab")
    assert "error" in result, "Expected error for unsupported molecule"
    ok("Unsupported molecule returns structured error (no crash)")


# ── 6. get_molecule_info ──────────────────────────────────────────────────────

def test_get_molecule_info() -> None:
    section("6. get_molecule_info")

    # 6a. All molecules
    result = get_molecule_info()
    assert result["count"] == 8, f"Expected 8 molecules, got {result['count']}"
    ok(f"All molecules: {result['count']} returned")

    # 6b. Specific molecule
    result = get_molecule_info(molecule="Nivolumab")
    assert result["target"] == "PD-1"
    assert "IgG4" in result["igg_subclass"]
    ok(f"Nivolumab: target={result['target']}, subclass={result['igg_subclass']}")

    # 6c. Adalimumab (molecule-specific Route rule)
    result = get_molecule_info(molecule="Adalimumab")
    assert any("IV Infusion" in n for n in result["notes"]), \
        "Adalimumab should have a note about the IV Infusion Route rule"
    ok("Adalimumab: Route-rule note present")

    # 6d. Case is ignored; a partial name gets a suggestion
    result = get_molecule_info(molecule="tocilizumab")
    assert result.get("molecule") == "Tocilizumab", result
    result = get_molecule_info(molecule="tocili")
    assert result["did_you_mean"] == ["Tocilizumab"], result
    ok("Case is ignored; partial name returns did_you_mean")

    # 6e. Unknown molecule
    result = get_molecule_info(molecule="Infliximab")
    assert "error" in result
    ok("Unknown molecule returns structured error (no crash)")


# ── 7. run_docker_command: versions and help (fast, no simulation) ───────────

def test_run_docker_command_fast() -> None:
    section("7. run_docker_command - versions + help (no simulation)")

    # In CI, Docker exists but the image does not, and the launcher would build it (15-30 min).
    commands = () if os.environ.get("PBPK_SKIP_DOCKER") else ("help", "versions")
    if not commands:
        info("PBPK_SKIP_DOCKER is set: skipping real Docker commands")
    for cmd in commands:
        result = run_docker_command(cmd)
        if result["status"] in ("OK", "MATCH"):
            ok(f"'{cmd}' → status={result['status']}")
        elif result["status"] == "STOPPED":
            info(f"'{cmd}' STOPPED: {result['stopped_message']} "
                 f"(Docker may not be running or image not built)")
        elif result["status"] == "ERROR":
            info(f"'{cmd}' ERROR: {result.get('error', result.get('full_output', ''))[:200]} "
                 f"(Docker may not be available)")
        else:
            fail(f"'{cmd}' returned unexpected status: {result['status']}")

    # Invalid command
    result = run_docker_command("invalid_command")
    assert result["status"] == "ERROR"
    assert "apriori" in result["allowed_values"]
    ok("Invalid command returns structured error (no crash)")


# ── 8. run_docker_command: apriori (optional, ~6 min) ───────────────────────

def test_run_docker_command_apriori() -> None:
    section("7b. run_docker_command - apriori (full run, ~6 min)")
    print("  Running apriori - this will take approximately 6 minutes...")
    result = run_docker_command("apriori")
    pp({k: v for k, v in result.items() if k != "full_output"})
    if result["status"] == "MATCH":
        ok("apriori → MATCH: all fold errors reproduce the published results")
    elif result["status"] == "DIFFERENT":
        fail("apriori → DIFFERENT: fold errors changed. Check data or script modifications.")
    elif result["status"] == "STOPPED":
        fail(f"apriori → STOPPED: {result['stopped_message']}")
    else:
        fail(f"apriori → unexpected status: {result['status']}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Test NAMLink MCP server tools")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Also run 'apriori' (Stage 1-5, ~6 min). Requires Docker.",
    )
    args = parser.parse_args()

    print("NAMLink MCP server - local tool tests")
    print(f"Repository root: {os.environ['PBPK_REPO_PATH']}")

    test_check_prerequisites()
    test_get_pipeline_status()
    test_get_fold_errors()
    test_get_accuracy_summary()
    test_query_study_design()
    test_get_molecule_info()
    test_run_docker_command_fast()

    if args.full:
        test_run_docker_command_apriori()

    section("All tests passed")
    print()


if __name__ == "__main__":
    main()
