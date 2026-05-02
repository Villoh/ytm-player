"""Custom command palette providers for ytm-player."""

from __future__ import annotations

from textual.command import DiscoveryHit, Hit, Provider


class YTMCommandProvider(Provider):
    """Custom command provider for ytm-player specific actions."""

    async def discover(self) -> None:
        """Yield discovery hits for ytm-player commands."""
        yield DiscoveryHit(
            "Theme: Set Current as Default",
            self.app.action_set_current_theme_as_default,
            help="Save the active theme to config.toml",
        )

    async def search(self, query: str) -> None:
        """Fuzzy search ytm-player commands."""
        matcher = self.matcher(query)
        commands = [
            (
                "Theme: Set Current as Default",
                self.app.action_set_current_theme_as_default,
                "Save the active theme to config.toml",
            ),
        ]
        for name, callback, help_text in commands:
            if (match := matcher.match(name)) > 0:
                yield Hit(
                    match,
                    matcher.highlight(name),
                    callback,
                    help=help_text,
                )
