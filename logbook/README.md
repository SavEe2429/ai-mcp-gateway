# Project Operational Logbook

This directory contains the operational logbook for this repository.

## Operational Rules

1. Append-Only: All entries are strictly append-only. Never modify, rewrite, or delete past entries.
2. Rotation Rule: When `logbook/current.md` exceeds 500 lines, rotate it to `YYYY-MM-DD_logbook.md`.
3. Immutable Archives: Rotated historical logs are strictly immutable archives and must never be
   altered retroactively.
4. Evidence-Based: Every entry must record tangible evidence (command executions, pass/fail status,
   and verified artifacts).
