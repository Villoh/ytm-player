"""Type-checking base class for app mixins.

At runtime this module exposes ``YTMHostBase = object`` so that mixins
inherit from ``object`` and behavior is unchanged.  Under
``TYPE_CHECKING`` it exposes a typed stub class describing
``YTMPlayerApp``'s full attribute surface — Pyright walks this stub
when analyzing each mixin in isolation, eliminating the
"Cannot access attribute X for class FooMixin" noise.

Zero runtime cost: the rich type definition lives behind
``TYPE_CHECKING`` and is never evaluated by the interpreter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from textual.app import App

    from ytm_player.config.keymap import KeyMap
    from ytm_player.config.settings import Settings
    from ytm_player.ipc import IPCServer
    from ytm_player.services.cache import CacheManager
    from ytm_player.services.discord_rpc import DiscordRPC
    from ytm_player.services.download import DownloadService
    from ytm_player.services.history import HistoryManager
    from ytm_player.services.lastfm import LastFMService
    from ytm_player.services.mediakeys import MediaKeysService
    from ytm_player.services.mpris import MPRISService
    from ytm_player.services.player import Player
    from ytm_player.services.queue import QueueManager
    from ytm_player.services.stream import StreamResolver
    from ytm_player.services.ytmusic import YTMusicService
    from ytm_player.ui.theme import ThemeColors

    class YTMHostBase(App[None]):
        """Type stub mirroring YTMPlayerApp's runtime instance surface.

        Mirrors every attribute set in ``YTMPlayerApp.__init__`` so
        Pyright stops complaining when a mixin reads ``self.player``,
        ``self.queue``, ``self.notify``, etc. in isolation.
        """

        # ── Configuration ──────────────────────────────────────────────
        settings: Settings
        keymap: KeyMap
        theme_colors: ThemeColors

        # ── Core services (initialized in on_mount; may be None pre-mount) ──
        ytmusic: YTMusicService | None
        player: Player | None
        queue: QueueManager
        stream_resolver: StreamResolver | None
        history: HistoryManager | None
        cache: CacheManager | None

        # ── Platform-specific media integrations ───────────────────────
        mpris: MPRISService | None
        mac_media: Any  # MacOSMediaService — Any to avoid platform import surprises
        mac_eventtap: Any  # MacOSEventTapService
        mediakeys: MediaKeysService | None

        # ── Optional integrations ──────────────────────────────────────
        discord: DiscordRPC | None
        lastfm: LastFMService | None
        downloader: DownloadService

        # ── Key input state ────────────────────────────────────────────
        _key_buffer: list[str]
        _count_buffer: str

        # ── Page / navigation state ────────────────────────────────────
        _current_page: str
        _current_page_kwargs: dict[str, Any]
        _nav_stack: list[tuple[str, dict]]
        _page_state_cache: dict[str, dict]
        _active_library_playlist_id: str | None
        _context_seq: int

        # ── Playback state tracking ────────────────────────────────────
        _track_start_position: float
        _consecutive_failures: int
        _advancing: bool
        _last_play_video_id: str
        _last_play_time: float

        # ── Pending resume from prior session ──────────────────────────
        _pending_resume_video_id: str | None
        _pending_resume_position: float

        # ── Lifecycle / IPC ────────────────────────────────────────────
        _poll_timer: Any
        _ipc_server: IPCServer | None
        _clean_exit: bool

        # ── Sidebar state ──────────────────────────────────────────────
        _sidebar_default: bool
        _sidebar_per_page: dict[str, bool]
        _lyrics_sidebar_open: bool

else:
    YTMHostBase = object  # noqa: PYI042 — runtime resolves to plain object
