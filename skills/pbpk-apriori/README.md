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

This skill covers the a priori workflow (`02_APriori_PBPK_Workflow`, Stages 1–3 and 5)
only. The following are outside its scope:

- Applying the workflow to a new antibody or target (see the repository README section
  "Applying the workflow to another mAb").
- The study-design workflow (`03_Study_Simulations`), which has not been validated in the
  Docker environment.

## Contents

| File | Description |
|---|---|
| `SKILL.md` | Agent skill definition, read by AI coding assistants |
| `README.md` | Reference documentation for human readers |
