#!/usr/bin/env bash
# Runner used inside the pbpk-mab-nam container (installed as /usr/local/bin/pbpk).
# The repository is expected to be mounted at /work.
set -uo pipefail

REPO=/work
SCRIPTS="02_APriori_PBPK_Workflow/Scripts"
RUN_FILE="02_APriori_PBPK_Workflow/SimsOutputs/latest_simulation_run.txt"
TABLE="02_APriori_PBPK_Workflow/SimsOutputs/Tables/Supplement_Fold_Error_Tornado_Data.csv"
LOGS="$REPO/_pbpk_logs"

say()  { printf '\n==> %s\n' "$*"; }
fail() { printf '\nSTOPPED: %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Usage: docker run --rm -v <repo folder>:/work pbpk-mab-nam <command>

Commands
  apriori      Run Part 1: Stages 1, 2, 3 and 5, then compare with the published table
  sensitivity  Run Stage 4 (local sensitivity analysis, about 15 minutes)
  compare      Only compare the current fold-error table with the committed one
  summary      Print how many predictions fall within 2-fold, by species and endpoint
  versions     Print the R, Quarto and package versions in this image
  help         Show this message
Logs are written to _pbpk_logs/ in the repository folder.
EOF
}

check_repo() {
  [[ -d "$REPO/00_Data" && -d "$REPO/$SCRIPTS" ]] ||
    fail "The repository is not mounted at /work. Run the command from the repository folder with -v \"\${PWD}:/work\" (PowerShell) or -v \"%cd%:/work\" (Command Prompt)."
  if grep -q 'mAb_data_clean.csv' "$REPO/$SCRIPTS/01_Setup_Configurations.qmd" &&
     [[ ! -f "$REPO/00_Data/Monkey/mAb_data_clean.csv" ]]; then
    fail "This checkout still has the v0.2.0 file-name bug. Use v0.2.1 or later (git checkout main)."
  fi
  mkdir -p "$LOGS"
}

render() {  # $1 = stage file name without extension
  local stage="$1" log="$LOGS/$1.log" start end
  say "Rendering $stage"
  start=$(date +%s)
  if ! quarto render "$REPO/$SCRIPTS/$stage.qmd" >"$log" 2>&1; then
    grep -E '^!|Error|Quitting' "$log" | head -n 5
    fail "$stage failed. Nothing after it was run. Full log: _pbpk_logs/$stage.log"
  fi
  end=$(date +%s)
  printf '    OK in %s s\n' "$((end - start))"
}

compare() {
  say "Comparing fold errors with the committed (published) table"
  Rscript --vanilla - "$REPO" "$TABLE" <<'EOF'
args <- commandArgs(trailingOnly = TRUE); repo <- args[1]; path <- args[2]
committed <- tryCatch(
  read.csv(text = system2("git", c("-C", repo, "show", paste0("HEAD:", path)), stdout = TRUE)),
  error = function(e) NULL)
current <- read.csv(file.path(repo, path))
if (is.null(committed)) { cat("No committed table to compare with.\n"); quit(status = 2) }
key <- c("Species", "Metric", "Molecule", "Dose_mg_kg")
m <- merge(committed, current, by = key, suffixes = c(".pub", ".new"), all = TRUE)
same_status <- identical(m$Evaluation_status.pub, m$Evaluation_status.new)
num <- !is.na(m$Fold_error.pub) | !is.na(m$Fold_error.new)
rel <- abs(m$Fold_error.new - m$Fold_error.pub) / abs(m$Fold_error.pub)
bad <- num & (is.na(rel) | rel > 1e-3)
cat(sprintf("Rows: published %d, new %d. Values differing by more than 0.1%%: %d\n",
            nrow(committed), nrow(current), sum(bad)))
if (nrow(committed) == nrow(current) && same_status && !any(bad)) {
  cat("MATCH: all fold errors reproduce the published results.\n")
} else {
  print(head(m[bad, c(key, "Fold_error.pub", "Fold_error.new")], 20))
  cat("DIFFERENT: see the rows above.\n"); quit(status = 1)
}
EOF
}

summary() {
  say "Accuracy summary (fold error within 0.5 to 2 = within 2-fold)"
  Rscript --vanilla - "$REPO/$TABLE" <<'EOF'
d <- read.csv(commandArgs(trailingOnly = TRUE)[1])
cat(sprintf("Scenario-endpoints: %d evaluated, %d not evaluable (e.g. too few late samples for clearance)\n\n",
            sum(d$Evaluation_status == "Evaluated"), sum(d$Evaluation_status != "Evaluated")))
e <- d[d$Evaluation_status == "Evaluated", ]
e$within <- e$Fold_error >= 0.5 & e$Fold_error <= 2
s <- aggregate(within ~ Species + Metric, data = e, FUN = function(x) c(n = length(x), ok = sum(x)))
s <- data.frame(Species = s$Species, Metric = s$Metric, Within_2fold = s$within[, "ok"], Evaluated = s$within[, "n"])
s$Percent <- round(100 * s$Within_2fold / s$Evaluated)
print(s[order(s$Species, s$Metric), ], row.names = FALSE)
EOF
}

cmd="${1:-help}"
case "$cmd" in
  help|-h|--help) usage ;;
  versions)
    R --version | head -n 1
    printf 'Quarto %s\n' "$(quarto --version)"
    Rscript -e 'for (p in c("rSharp","ospsuite","esqlabsR")) cat(p, format(packageVersion(p)), "\n")'
    dotnet --list-runtimes ;;
  apriori)
    check_repo
    before=$(tr -d '\r' < "$REPO/$RUN_FILE" 2>/dev/null || true)
    render 01_Setup_Configurations
    render 02_Run_Sims
    after=$(tr -d '\r' < "$REPO/$RUN_FILE" 2>/dev/null || true)
    [[ -n "$after" && "$after" != "$before" ]] ||
      fail "Stage 2 did not record a new simulation run; stopping so old results are not reused."
    printf '    New simulation run: %s\n' "$after"
    render 03_Process_Sims_Outputs
    render 05_Supplementary_Fold_Error_Tornado_Plot
    compare
    say "Done. Main report: $SCRIPTS/03_Process_Sims_Outputs.html" ;;
  sensitivity)
    check_repo
    render 04_LocalSensitivityAnalysis
    say "Done. Report: $SCRIPTS/04_LocalSensitivityAnalysis.html" ;;
  compare)
    check_repo; compare ;;
  summary)
    check_repo; summary ;;
  *)
    usage; fail "Unknown command: $cmd" ;;
esac
