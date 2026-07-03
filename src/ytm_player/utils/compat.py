"""Python 3.10 compatibility shims.

Backports stdlib symbols added in 3.11+ so the codebase runs on the 3.10
floor. Guards use ``sys.version_info >= (3, 11)`` (which Pyright narrows
correctly) so 3.11+ imports the real stdlib implementation.
"""

from __future__ import annotations

import sys

if sys.version_info >= (3, 11):
    from enum import StrEnum, auto
else:
    # Python 3.10 backport — match StrEnum.auto() lowercase-name behavior.
    from enum import Enum, auto

    class StrEnum(str, Enum):
        @staticmethod
        def _generate_next_value_(name, start, count, last_values):
            return name.lower()


__all__ = ["StrEnum", "auto"]
