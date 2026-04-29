#!/usr/bin/env python3
"""Regenerate .SRCINFO from a PKGBUILD without requiring makepkg/Arch.

Usage: ./scripts/regenerate_srcinfo.py aur/PKGBUILD aur/.SRCINFO
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_SCALAR_FIELDS = (
    "pkgname",
    "pkgver",
    "pkgrel",
    "pkgdesc",
    "url",
    "epoch",
    "install",
    "changelog",
)
_ARRAY_FIELDS = (
    "arch",
    "license",
    "groups",
    "depends",
    "makedepends",
    "checkdepends",
    "optdepends",
    "provides",
    "conflicts",
    "replaces",
    "backup",
    "options",
    "source",
    "validpgpkeys",
    "noextract",
    "md5sums",
    "sha1sums",
    "sha224sums",
    "sha256sums",
    "sha384sums",
    "sha512sums",
)


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        return s[1:-1]
    return s


def _parse_array(value: str) -> list[str]:
    inner = value.strip()
    if inner.startswith("(") and inner.endswith(")"):
        inner = inner[1:-1]
    parts: list[str] = []
    current: list[str] = []
    in_quote: str | None = None
    for ch in inner:
        if in_quote:
            if ch == in_quote:
                in_quote = None
                parts.append("".join(current))
                current = []
            else:
                current.append(ch)
        else:
            if ch in ("'", '"'):
                in_quote = ch
            elif ch.isspace():
                if current:
                    parts.append("".join(current))
                    current = []
            else:
                current.append(ch)
    if current:
        parts.append("".join(current))
    return [p for p in parts if p]


def _expand_vars(value: str, scalars: dict[str, str]) -> str:
    """Expand simple ``${var}`` / ``$var`` references using already-parsed scalars.

    PKGBUILDs commonly reference ``${url}`` or ``${pkgname}`` inside arrays like
    ``source=()``. We only expand variables that we have already parsed as scalar
    fields — anything else is left untouched.
    """

    def repl(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2)
        return scalars.get(name, match.group(0))

    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)", repl, value)


def parse_pkgbuild(content: str) -> dict[str, object]:
    """Parse a PKGBUILD into a dict of field -> value (str or list[str])."""
    result: dict[str, object] = {}
    scalars: dict[str, str] = {}
    line_iter = iter(content.splitlines())
    for raw in line_iter:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if not m:
            continue
        key, value = m.group(1), m.group(2)
        if value.startswith("(") and not value.endswith(")"):
            buf = [value]
            for cont in line_iter:
                buf.append(cont)
                if cont.rstrip().endswith(")"):
                    break
            value = " ".join(buf)
        if key in _ARRAY_FIELDS:
            entries = _parse_array(value)
            result[key] = [_expand_vars(e, scalars) for e in entries]
        elif key in _SCALAR_FIELDS:
            stripped = _expand_vars(_strip_quotes(value), scalars)
            result[key] = stripped
            scalars[key] = stripped
    return result


def emit_srcinfo(parsed: dict[str, object]) -> str:
    """Emit a .SRCINFO string for *parsed*. Spec: https://wiki.archlinux.org/title/.SRCINFO."""
    pkgname = parsed.get("pkgname", "")
    if isinstance(pkgname, list):
        pkgname = pkgname[0] if pkgname else ""
    lines: list[str] = []
    lines.append(f"pkgbase = {pkgname}")
    for field in _SCALAR_FIELDS:
        if field == "pkgname":
            continue
        v = parsed.get(field)
        if v is not None and v != "":
            lines.append(f"\t{field} = {v}")
    for field in _ARRAY_FIELDS:
        v = parsed.get(field)
        if isinstance(v, list):
            for entry in v:
                lines.append(f"\t{field} = {entry}")
    lines.append("")
    lines.append(f"pkgname = {pkgname}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: regenerate_srcinfo.py <PKGBUILD> <out_SRCINFO>", file=sys.stderr)
        return 2
    pkgbuild_path = Path(sys.argv[1])
    srcinfo_path = Path(sys.argv[2])
    parsed = parse_pkgbuild(pkgbuild_path.read_text(encoding="utf-8"))
    srcinfo_path.write_text(emit_srcinfo(parsed), encoding="utf-8")
    print(f"Wrote {srcinfo_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
