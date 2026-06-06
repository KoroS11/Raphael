# Raphael — Agent Prompt Guide and Stage Index

## How to Use These Documents

This folder contains one prompt file per build stage. Each file is a self-contained instruction set meant to be pasted directly into an AI coding agent such as Cursor, Claude Code, or Windsurf.

The correct workflow is:

```
1. Open your agent
2. Paste the contents of the stage file as your prompt
3. Also attach the relevant docs from the docs/ folder as context
4. Let the agent execute the stage completely
5. Run the verification checklist at the bottom of each stage file
6. Only move to the next stage after all checks pass
```

Never skip stages. Each stage produces artifacts that the next stage depends on.

---

## Context Files to Always Include

Paste or attach these three files as context in every agent session regardless of which stage you are on:

```
docs/SYSTEM_ARCHITECTURE.md      — How every subsystem connects
docs/TECHNICAL_SPECIFICATION.md  — Exact dependency versions and config
docs/DATA_SOURCES.md             — All 28 data sources with endpoints
```

---

## Stage Index

| Stage | File | What It Builds | Duration Estimate |
