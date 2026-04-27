"""Extract a release section from CHANGELOG.md.

Used by the Publish workflow to populate the GitHub Release body.
Errors loudly (exit 1) if the requested section is missing — preferable
to a silent fallback that ships an empty release.

Usage:
    python extract_changelog.py vX.Y.Z CHANGELOG.md > release_notes.md
"""

from __future__ import annotations

import re
import sys


def extract_section(changelog: str, version: str) -> str:
    """Return the changelog body for ``version`` (e.g. ``"1.7.2"``).

    The header line is included; trailing ``---`` separators and blank
    lines are stripped. Raises ``ValueError`` if no matching section is
    found.
    """
    header_re = re.compile(rf"^### v{re.escape(version)}(\s|$)")
    next_release_re = re.compile(r"^### v\d")

    captured: list[str] = []
    inside = False
    for line in changelog.splitlines(keepends=True):
        if header_re.match(line):
            inside = True
            captured.append(line)
            continue
        if inside and next_release_re.match(line):
            break
        if inside:
            captured.append(line)

    if not captured:
        raise ValueError(f"no '### v{version}' section found in CHANGELOG")

    while captured and captured[-1].strip() in ("", "---"):
        captured.pop()

    return "".join(captured)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"usage: {argv[0]} <tag> <changelog-path>", file=sys.stderr)
        return 2

    tag, path = argv[1], argv[2]
    version = tag.removeprefix("v")

    with open(path, encoding="utf-8") as f:
        changelog = f.read()

    try:
        section = extract_section(changelog, version)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    sys.stdout.write(section)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
