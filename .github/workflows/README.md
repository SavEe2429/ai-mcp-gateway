# GitHub Actions Workflows Runbook

This directory contains continuous integration and automated release orchestration workflows for
`ai-mcp-gateway`.

---

## 1. Workflow Catalog

| Workflow File                | Purpose                                                                                              | Triggers                                                     | Required Permissions                 |
| :--------------------------- | :--------------------------------------------------------------------------------------------------- | :----------------------------------------------------------- | :----------------------------------- |
| [`ci.yml`](ci.yml)           | Multi-tier quality gate (lint, lock parity, Gitleaks secret scan, tests, build)                      | `push` on `main`/`master`, `pull_request` on `main`/`master` | `contents: read`                     |
| [`release.yml`](release.yml) | Automated SemVer release, Windows `.exe` build, changelog promotion, tagging, and asset distribution | `push` on `release/v*` or `workflow_dispatch`                | `contents: write`, `packages: write` |

---

## 2. Secrets Reference

| Secret Name    | Required By   | Description                                                                                                       |
| :------------- | :------------ | :---------------------------------------------------------------------------------------------------------------- |
| `GITHUB_TOKEN` | `release.yml` | Default GitHub Actions token used for pushing tags, committing changelog updates, and publishing GitHub Releases. |

---

## 3. Branch Protection Policies

To ensure stability on main branches, configure the following rules in GitHub Repository Settings:

- **Target Branches:** `main`, `master`
- **Require Status Checks to Pass:**
  - `Code Quality (Lint & Lock)` (defined in `ci.yml`)
  - `Test Suite (ubuntu-latest)`
  - `Test Suite (windows-latest)`
  - `Build (python-dist)`
  - `Build (windows-bundle)`
  - `CI Summary`
- **Require Pull Request Reviews:** Minimum 1 approving review.
- **Enforce Linear History:** Recommended (squash or rebase merging).

---

## 4. Local Workflow Execution

Developers can verify pipeline stages locally without pushing to GitHub using the native `uv`
runner:

```bash
# Tier 1: Static Analysis & Linting
uv run ruff check src/ tests/ packaging/ templates/ .github/scripts/release/

# Tier 2: Unit and Integration Tests
uv run pytest

# Tier 3: Lockfile Consistency Check
uv lock --check

# Tier 4: Distribution & Binary Build Verification
uv build
uv run python packaging/build.py --mode onedir
```
