#!/usr/bin/env python3
"""Drive mcp/server.py over the real stdio MCP protocol, including hostile inputs.

Run from the repository root:
    python mcp/test_stdio_mcp.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = Path(__file__).resolve().parent.parent
FAILURES = 0


def check(cond, msg):
    global FAILURES
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAILURES += 1


def body(res):
    if res.is_error:
        return {"_tool_error": " ".join(getattr(c, "text", "") for c in res.content)}
    sc = res.structured_content
    if sc is None:
        sc = json.loads(res.content[0].text)
    return sc.get("result", sc) if isinstance(sc, dict) and set(sc) == {"result"} else sc


async def main():
    env = {**os.environ, "PBPK_REPO_PATH": str(REPO)}
    params = StdioServerParameters(command=sys.executable, args=[str(REPO / "mcp" / "server.py")], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            init = await s.initialize()
            check(bool(init.instructions) and "Stages 6-8" in init.instructions, "server instructions reach the client")
            names = {t.name for t in (await s.list_tools()).tools}
            check(len(names) == 7, f"7 tools listed: {sorted(names)}")

            async def call(name, args):
                return body(await s.call_tool(name, args))

            r = await call("get_fold_errors", {})
            check((r["total_rows"], r["evaluated_count"], r["within_2fold_count"]) == (132, 109, 96),
                  "unfiltered table: 132 rows, 109 evaluated, 96 within 2-fold")
            r = await call("get_fold_errors", {"species": " monkey ", "metric": "CMAX", "molecule": "nivolumab"})
            check(r.get("total_rows", 0) > 0 and all(x["molecule"] == "Nivolumab" for x in r["rows"]),
                  "case and spacing in filters are ignored")
            for field, value in [("species", "Rat"), ("metric", "AUC"), ("molecule", "Nivo"),
                                 ("evaluation_status", "maybe")]:
                r = await call("get_fold_errors", {field: value})
                check(r.get("field") == field and r.get("allowed_values"), f"unknown {field} lists the allowed values")
            r = await call("get_fold_errors", {"species": 123})
            check("_tool_error" in r, "wrong argument type is a tool error, not a crash")

            r = await call("query_study_design", {"molecule": "golimumab", "variability_cv": 30, "n_per_group": 3,
                                                  "design": "5 DOSE GROUPS"})
            check(len(r.get("overall_success", [])) == 1 and r["overall_success"][0]["variability_cv"] == 0.3,
                  "study design: lower case, 30 read as 30% CV, upper-case design")
            for args, field in [({"molecule": "Adalimumab"}, "molecule"),
                                ({"molecule": "Golimumab", "design": "2"}, "design"),
                                ({"molecule": "Golimumab", "n_per_group": 4}, "n_per_group"),
                                ({"molecule": "Golimumab", "dose_mg_kg": 2}, "dose_mg_kg"),
                                ({"molecule": "Golimumab", "endpoint": "AUC"}, "endpoint")]:
                r = await call("query_study_design", args)
                check(r.get("field") == field, f"study design rejects bad {field} with allowed values")
            r = await call("query_study_design", {"molecule": "Golimumab", "design": "3 dose groups",
                                                  "dose_mg_kg": 3, "endpoint": "Cmax"})
            check(r.get("fold_error_detail") == [] and "not part of" in r.get("note", ""),
                  "dose outside the chosen design is explained")
            r = await call("query_study_design", {"molecule": "Nivolumab", "design": "5 dose groups", "n_per_group": 6,
                                                  "variability_cv": 0.6, "dose_mg_kg": 30, "endpoint": "Terminal clearance"})
            check(len(r.get("fold_error_detail", [])) == 1, "fully specified study-design cell returns one detail row")
            r = await call("query_study_design", {})
            check("_tool_error" in r, "missing required molecule is a tool error")

            r = await call("get_molecule_info", {"molecule": "tocilizumab"})
            check(r.get("molecule") == "Tocilizumab", "molecule lookup ignores case")
            r = await call("get_molecule_info", {"molecule": "x" * 100000})
            check("error" in r and len(json.dumps(r)) < 2000, "100 kB molecule name gives a short error")
            r = await call("get_molecule_info", {"molecule": ""})
            check(r.get("did_you_mean") is None, "empty molecule name suggests nothing")

            for cmd in ["apriori; echo pwned", "../../etc/passwd", "", "rm -rf /"]:
                r = await call("run_docker_command", {"command": cmd})
                check(r.get("status") == "ERROR" and "allowed_values" in r, f"command {cmd!r} is refused")

            r = await call("get_pipeline_status", {})
            check(r["within_2fold_count"] == 96 and "109 evaluated" in r["note"], "pipeline status and note are correct")
            r = await call("check_prerequisites", {})
            check(any(c["check"] == "Checkout is v0.2.1 or later" and c["status"] == "PASS" for c in r["checks"]),
                  "checkout-version check passes on this checkout")
            r = await s.call_tool("no_such_tool", {})
            check(r.is_error, "unknown tool is a tool error")

    print("All stdio MCP checks passed" if not FAILURES else f"{FAILURES} stdio MCP check(s) FAILED")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    asyncio.run(main())
