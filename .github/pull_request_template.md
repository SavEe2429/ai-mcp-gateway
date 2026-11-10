## Description

Provide a brief summary of the changes proposed in this Pull Request and reference any related issues (e.g., `Closes #12`).

## Change Classification

Select the applicable change type matching Conventional Commits:

- [ ] `feat`: A new feature or capability
- [ ] `fix`: A bug fix or patch
- [ ] `refactor`: Code reorganization with no behavior change
- [ ] `perf`: Performance optimization
- [ ] `test`: Test suite addition or verification enhancement
- [ ] `docs`: Documentation updates or additions
- [ ] `build`: Packaging or build system updates (including PyInstaller `.exe`)
- [ ] `ci`: CI/CD workflow updates
- [ ] `chore`: Maintenance or dependency updates

## Contributor Checklist

- [ ] Code follows repository architectural boundaries (`src/ai_mcp_gateway/`, clean root, data isolation).
- [ ] New and refactored Python modules follow `templates/python/script_template.py` (9-section structure) and granular exception handling.
- [ ] `uv run ruff check src/ tests/ packaging/` passes with zero warnings.
- [ ] `uv run pytest` passes with all tests hermetic (no personal `data/` or `workspace/` artifacts committed).
- [ ] New text files enforce LF (`\n`) line endings.
- [ ] `CHANGELOG.md` is updated under `[Unreleased]` when user-facing behavior changes.

## Reviewer Checklist

- [ ] Architecture and workspace sandbox boundaries (`fs.safe_path()`) are preserved.
- [ ] Localhost dashboard restrictions (`/ui`, `/api/ui`, `/ws/ui`) and token protections remain intact.
- [ ] Tests cover edge cases without relying on local machine state.
