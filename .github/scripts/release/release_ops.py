"""Release Operations Script for ai-mcp-gateway.

Cross-platform release orchestration tool providing changelog promotion,
release notes generation, index updating, pyproject version sync, and GitHub
release body formatting.
"""

## ---------- (01) STANDARD LIBRARY IMPORTS ----------------------------------------- ##
import argparse
import re
import sys
from pathlib import Path

## ---------- (02) THIRD-PARTY IMPORTS ---------------------------------------------- ##
## ---------- (03) LOCAL APPLICATION/LIBRARY-SPECIFIC IMPORTS ----------------------- ##
## ---------- (04) CONSTANTS -------------------------------------------------------- ##
DEFAULT_CHANGELOG_PATH: str = "CHANGELOG.md"
DEFAULT_NOTES_DIR: str = "Docs/public/release-notes"
DEFAULT_NOTES_INDEX: str = "Docs/public/release-notes/README.md"
DEFAULT_CHECKSUMS_PATH: str = "dist/SHA256SUMS.txt"
DEFAULT_RELEASE_BODY_PATH: str = "dist/RELEASE_BODY.md"
DEFAULT_PYPROJECT_PATH: str = "pyproject.toml"

## ---------- (05) ENUMS ------------------------------------------------------------ ##
# No module-level enums required.

## ---------- (06) CLASS DEFINITIONS ------------------------------------------------ ##
# No module-level classes required.


## ---------- (07) PUBLIC FUNCTIONS ------------------------------------------------- ##
def update_changelog(version: str, date: str, changelog_path: str = DEFAULT_CHANGELOG_PATH) -> None:
    """Promote [Unreleased] section to version header and insert new empty [Unreleased]."""
    path = Path(changelog_path)
    if not path.is_file():
        print(f"ERROR: {changelog_path} not found", file=sys.stderr)
        sys.exit(1)

    content = path.read_text(encoding="utf-8")
    if re.search(rf"^## \[{re.escape(version)}\]", content, re.MULTILINE):
        print(f"[{version}] already exists in {changelog_path}; skipping promotion.")
        return

    target = "## [Unreleased]"
    replacement = f"## [Unreleased]\n\n## [{version}] - {date}"

    if target not in content:
        print("ERROR: '## [Unreleased]' section not found in CHANGELOG.md", file=sys.stderr)
        sys.exit(1)

    new_content = content.replace(target, replacement, 1)
    path.write_text(new_content, encoding="utf-8")
    print(f"Promoted [Unreleased] section to [{version}] - {date} in {changelog_path}")


def generate_release_notes(
    version: str,
    changelog_path: str = DEFAULT_CHANGELOG_PATH,
    output_dir: str = DEFAULT_NOTES_DIR,
) -> None:
    """Extract version section from CHANGELOG.md into standalone markdown file."""
    path = Path(changelog_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"v{version}.md"

    if not path.is_file():
        body = f"# Release Notes - v{version}\n\nAutomated release build for version {version}.\n"
    else:
        text = path.read_text(encoding="utf-8")
        pattern = rf"## \[{re.escape(version)}\][^\n]*\n(.*?)(?=\n## \[|\Z)"
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            body = (
                f"# Release Notes - v{version}\n\nAutomated release build for version {version}.\n"
            )
        else:
            body_content = match.group(1).strip()
            body = f"# Release Notes - v{version}\n\n{body_content}\n"

    out_file.write_text(body, encoding="utf-8")
    print(f"Generated release notes file at {out_file}")


def update_release_notes_index(
    version: str, date: str, index_file: str = DEFAULT_NOTES_INDEX
) -> None:
    """Update release notes index README table with latest version link."""
    path = Path(index_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    header = (
        "# Release Notes Index\n\n"
        "This directory archives standalone release notes for each published version of ai-mcp-gateway.\n\n"
        "| Version | Release Date | Release Notes Document |\n"
        "| :--- | :--- | :--- |\n"
    )

    if not path.is_file():
        content = header
    else:
        content = path.read_text(encoding="utf-8")
        if "| Version |" not in content:
            content = header + content

    new_row = f"| v{version} | {date} | [v{version}.md](v{version}.md) |"
    if f"v{version}.md" not in content:
        content = content.rstrip() + f"\n{new_row}\n"
        path.write_text(content, encoding="utf-8")
        print(f"Added v{version} to {index_file}")
    else:
        print(f"v{version} already indexed in {index_file}")


def build_release_body(
    version: str,
    notes_file: str = "",
    checksum_file: str = DEFAULT_CHECKSUMS_PATH,
    output_file: str = DEFAULT_RELEASE_BODY_PATH,
) -> None:
    """Build release markdown body combining notes and SHA-256 checksums."""
    if not notes_file:
        notes_file = f"{DEFAULT_NOTES_DIR}/v{version}.md"

    body_parts = []
    notes_path = Path(notes_file)
    if notes_path.is_file():
        body_parts.append(notes_path.read_text(encoding="utf-8").strip())
    else:
        body_parts.append(f"# Release Notes - v{version}\n\nAutomated production release.")

    checksum_path = Path(checksum_file)
    if checksum_path.is_file():
        checksums = checksum_path.read_text(encoding="utf-8").strip()
        body_parts.append(
            f"## Release Verification & Checksums (SHA-256)\n\n```text\n{checksums}\n```"
        )

    final_body = "\n\n".join(body_parts) + "\n"
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(final_body, encoding="utf-8")
    print(f"Generated GitHub release body at {output_file}")


def sync_pyproject_version(version: str, pyproject_path: str = DEFAULT_PYPROJECT_PATH) -> None:
    """Synchronize [project].version in pyproject.toml with the target release version."""
    path = Path(pyproject_path)
    if not path.is_file():
        print(f"ERROR: {pyproject_path} not found", file=sys.stderr)
        sys.exit(1)

    content = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'^(version\s*=\s*")[^"]+(")',
        rf"\g<1>{version}\g<2>",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    if count == 0:
        print(f"ERROR: Could not find version field in {pyproject_path}", file=sys.stderr)
        sys.exit(1)

    path.write_text(updated, encoding="utf-8")
    print(f"Updated version to {version} in {pyproject_path}")


## ---------- (08) PRIVATE FUNCTIONS ------------------------------------------------ ##
def _parse_args() -> argparse.Namespace:
    """Parse CLI release operation subcommands."""
    parser = argparse.ArgumentParser(description="AI MCP Gateway Release Operations CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    p_changelog = subparsers.add_parser("update-changelog")
    p_changelog.add_argument("version", help="Version string (e.g. 0.2.0)")
    p_changelog.add_argument("date", help="Release date (e.g. 2026-11-03)")
    p_changelog.add_argument("--file", default=DEFAULT_CHANGELOG_PATH, help="Path to CHANGELOG.md")

    p_notes = subparsers.add_parser("generate-notes")
    p_notes.add_argument("version", help="Version string (e.g. 0.2.0)")
    p_notes.add_argument("--changelog", default=DEFAULT_CHANGELOG_PATH, help="Path to CHANGELOG.md")
    p_notes.add_argument("--out-dir", default=DEFAULT_NOTES_DIR, help="Output directory")

    p_index = subparsers.add_parser("update-index")
    p_index.add_argument("version", help="Version string (e.g. 0.2.0)")
    p_index.add_argument("date", help="Release date (e.g. 2026-11-03)")
    p_index.add_argument("--file", default=DEFAULT_NOTES_INDEX, help="Path to index README.md")

    p_body = subparsers.add_parser("build-body")
    p_body.add_argument("version", help="Version string (e.g. 0.2.0)")
    p_body.add_argument("--notes", default="", help="Path to version notes markdown")
    p_body.add_argument(
        "--checksums", default=DEFAULT_CHECKSUMS_PATH, help="Path to SHA256SUMS.txt"
    )
    p_body.add_argument("--out", default=DEFAULT_RELEASE_BODY_PATH, help="Output release body file")

    p_sync = subparsers.add_parser("sync-pyproject")
    p_sync.add_argument("version", help="Version string (e.g. 0.2.0)")
    p_sync.add_argument("--file", default=DEFAULT_PYPROJECT_PATH, help="Path to pyproject.toml")

    return parser.parse_args()


## ---------- (09) MAIN EXECUTION --------------------------------------------------- ##
def main() -> int:
    """Execute the requested release operation subcommand."""
    args = _parse_args()
    if args.subcommand == "update-changelog":
        update_changelog(args.version, args.date, args.file)
    elif args.subcommand == "generate-notes":
        generate_release_notes(args.version, args.changelog, args.out_dir)
    elif args.subcommand == "update-index":
        update_release_notes_index(args.version, args.date, args.file)
    elif args.subcommand == "build-body":
        build_release_body(args.version, args.notes, args.checksums, args.out)
    elif args.subcommand == "sync-pyproject":
        sync_pyproject_version(args.version, args.file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
