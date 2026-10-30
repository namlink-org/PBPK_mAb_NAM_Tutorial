# pbpk-apriori agent skill

This folder contains an agent skill for AI coding assistants. The skill enables an
assistant to run, reproduce and verify the a priori PBPK monoclonal-antibody workflow
through the containerised Docker environment, without generating simulation code of its own.

## Overview

`SKILL.md` is a plain-text instruction file in the open Agent Skills format. It specifies
the Docker commands available in this repository, the rules the assistant must observe
(derived from the repository README section "Appropriate uses of an LLM"), and the
criteria for reporting a run as successful or failed. An assistant configured with this
skill drives the fixed, tested runner rather than writing independent R or shell code,
which preserves reproducibility.

## Capabilities

An assistant operating under this skill can:

- Execute the full a priori workflow (`apriori`) and verify that fold errors match the
  committed published table.
- Report the within-2-fold accuracy summary by species and endpoint (`summary`).
- Re-run the comparison against the published table without re-simulating (`compare`).
- Execute the optional local sensitivity analysis (`sensitivity`).
- Report software versions inside the image (`versions`).
- Answer detailed questions about the eight reference mAbs, their IgG subclasses, and
  their mechanistic PKML parameter values.
- Guide users through the full 21-column study-design CSV schema and the administration
  duration rules that govern infusion time resolution.
- Explain the distinction between generated and input Excel workbooks and the role of
  each stage (1–5) in the pipeline.
- Diagnose common error messages and guide users through fixes (ospsuite version
  incompatibility, wrong mount, missing Docker Desktop, etc.).
- Walk a user through adding a new mAb to the dataset following the six-step checklist.
- Interpret PK endpoint calculations (AUC, CL, Vss, t½) and the fold-error evaluability
  criteria applied at Stage 3.
- Clarify the primary vs secondary study-design distinction and the 200-checkpoint
  sensitivity structure.
- Describe software licensing for code (MIT), data/docs (CC BY 4.0) and OSP packages
  (GPL-2.0).

The skill explicitly prohibits the assistant from inventing or modifying biological
parameters, editing data or model files without direct instruction, or reporting a
successful result unless the runner outputs `MATCH`.

## Prerequisites

Docker Desktop must be installed and running before any skill command can be executed.
Refer to [`../README.md`](../README.md) for environment setup and platform-specific
instructions.

## Integration

### Claude Code

Claude Code reads `skills/` directories automatically when the repository is the working
directory. No additional configuration is required; the skill is available under the name
`pbpk-apriori`. Requests to run the workflow, reproduce the results, or verify fold errors
will invoke the skill.

### Cursor

Add `SKILL.md` as context in the Cursor chat panel using `@SKILL.md`, then submit the
request. Cursor will follow the commands and constraints defined in the skill file.

### GitHub Copilot (VS Code)

Reference the skill file in the Copilot Chat panel with `#file:skills/pbpk-apriori/SKILL.md`
before submitting a request. Copilot will incorporate the skill's instructions as context.

### Other AI assistants

The contents of `SKILL.md` can be included in the system prompt or context window of any
AI assistant that accepts Markdown-formatted instructions. The file is self-contained and
requires no additional context.

## Scope

This skill covers the a priori workflow (`02_APriori_PBPK_Workflow`, Stages 1–5), the
eight reference mAbs, the study-design CSV schema, and the Docker environment. The
following are outside its scope:

- The study-design simulation workflow (`03_Study_Simulations`, Stages 6–8), which is not
  available as a Docker command and has not been validated in the containerised environment.
- Modifying or extending the underlying PK-Sim/MoBi models directly.

## Contents

| File | Description |
|---|---|
| `SKILL.md` | Agent skill definition, read by AI coding assistants |
| `README.md` | Reference documentation for human readers |
