"""Command palette provider for ytm-player."""

from __future__ import annotations

from textual.command import Hit, Hits, Provider


class AppCommandProvider(Provider):
    """Provides application-wide commands for the Textual command palette."""

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for name, help_text, callback in self._commands():
            score = matcher.match(name)
            if score > 0:
                yield Hit(
                    score=score,
                    match_display=matcher.highlight(name),
                    command=callback,
                    help=help_text,
                )

    async def discover(self) -> Hits:
        for name, help_text, callback in self._commands():
            yield Hit(
                score=0,
                match_display=name,
                command=callback,
                help=help_text,
            )

    def _commands(self) -> list[tuple[str, str, object]]:
        app = self.app
        return [
            ("Clear Queue", "Remove all tracks from the play queue", app._cmd_clear_queue),
        ]
