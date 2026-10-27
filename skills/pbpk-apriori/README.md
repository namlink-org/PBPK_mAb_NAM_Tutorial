# pbpk-apriori skill

This folder contains an agent skill for the PBPK mAb a priori workflow.

## What is a skill?

`SKILL.md` is a plain-text instruction file for AI coding assistants. When an assistant
reads it, it learns the commands available in the Docker environment, the rules it must
follow (from the repository README), and exactly how to interpret a successful or failed
run. The assistant then runs the workflow through Docker rather than writing its own
simulation code.

## What does this skill let an AI assistant do?

- Run the full a priori workflow (`apriori` command) and confirm the fold errors match the
  published table.
- Print the accuracy summary (`summary`).
- Re-run the comparison against the published table without re-simulating (`compare`).
- Run the optional sensitivity analysis (`sensitivity`).
- Report software versions inside the image (`versions`).

The skill also tells the assistant what it must **not** do: invent biological parameters,
edit data or model files without explicit instruction, or report success unless the runner
prints `MATCH`.

## Prerequisites

Docker Desktop must be installed and running on your computer before the skill can be used.
See [`../README.md`](../README.md) for setup.

## Using the skill with different AI tools

### Claude Code (Anthropic)

Place this repository in your working directory. Claude Code reads `skills/` folders
automatically when they exist in the project root. The skill is named `pbpk-apriori`.

To invoke it, ask Claude Code to run the a priori workflow, reproduce the results, or
check the fold errors. It will use this skill to drive Docker rather than writing its own
R or shell code.

### Cursor

Open the repository as a Cursor project. In the chat panel, attach `SKILL.md` as context
(drag it in, or use `@SKILL.md`), then ask Cursor to run the workflow. Cursor will follow
the commands and rules in the skill file.

### GitHub Copilot (VS Code)

Open the repository in VS Code with Copilot enabled. In the Copilot Chat panel, use
`#file:skills/pbpk-apriori/SKILL.md` to add the skill as context before asking it to
run the workflow.

### Any other tool that reads Markdown context

Paste the contents of `SKILL.md` into the system prompt or context window of any AI
assistant. The file is self-contained: it lists the commands, rules, and interpretation
guidance the assistant needs.

## What the skill does NOT cover

- Adding a new antibody or target (see the repository README, "Applying the workflow to
  another mAb").
- The study-design part (`03_Study_Simulations`): this runs for several hours and has not
  been tested in Docker.

## Files in this folder

| File | Purpose |
|---|---|
| `SKILL.md` | The agent skill read by AI assistants |
| `README.md` | This file — for human readers |
