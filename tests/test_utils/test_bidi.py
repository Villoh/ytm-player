"""Tests for BiDi utilities (bidi.py).

With bidi_mode="auto" (default), reorder_rtl_line and wrap_rtl_line
pass text through unchanged — reordering is disabled because it causes
double-reversal on BiDi terminals and wrong reading order on non-BiDi
terminals.

Tests for the internal _do_reorder function verify the UAX #9 logic
still works when bidi_mode="reorder" is explicitly set.
"""

import pytest

from ytm_player.utils.bidi import (
    FSI,
    PDI,
    _do_reorder,
    has_rtl,
    isolate_bidi,
    reorder_rtl_line,
    reset_bidi_cache,
    wrap_rtl_line,
)

# ── has_rtl ──────────────────────────────────────────────────────────


class TestHasRtl:
    def test_pure_english(self):
        assert has_rtl("Hello World") is False

    def test_pure_arabic(self):
        assert has_rtl("مرحبا بالعالم") is True

    def test_pure_hebrew(self):
        assert has_rtl("שלום עולם") is True

    def test_mixed_arabic_english(self):
        assert has_rtl("Hello عالم") is True

    def test_empty_string(self):
        assert has_rtl("") is False

    def test_numbers_only(self):
        assert has_rtl("12345") is False

    def test_arabic_presentation_forms(self):
        # U+FE70 = Arabic Presentation Form-B
        assert has_rtl("\ufe70") is True

    def test_emoji_no_rtl(self):
        assert has_rtl("\U0001f3b5 Music") is False


# ── Default mode (auto/passthrough): text passes through unchanged ───


class TestDefaultPassthrough:
    """With bidi_mode='auto', reorder functions return text unchanged."""

    @pytest.fixture(autouse=True)
    def _reset_cache(self):
        reset_bidi_cache()
        yield
        reset_bidi_cache()

    def test_reorder_returns_unchanged(self):
        text = "يا ليل يا عين"
        assert reorder_rtl_line(text) == text

    def test_wrap_returns_unchanged(self):
        text = "يا ليل يا عين"
        assert wrap_rtl_line(text, 80) == text

    def test_reorder_pure_english_unchanged(self):
        assert reorder_rtl_line("Hello World") == "Hello World"

    def test_reorder_empty(self):
        assert reorder_rtl_line("") == ""

    def test_wrap_empty(self):
        assert wrap_rtl_line("", 80) == ""

    def test_wrap_pure_english_unchanged(self):
        assert wrap_rtl_line("Hello World", 80) == "Hello World"


# ── _do_reorder (internal UAX #9 logic) ─────────────────────────────


class TestDoReorderPureRtl:
    def test_two_arabic_words_reversed(self):
        assert _do_reorder("عيون القلب") == "القلب عيون"

    def test_four_arabic_words(self):
        assert _do_reorder("يا ليل يا عين") == "عين يا ليل يا"

    def test_arabic_with_tashkeel(self):
        assert _do_reorder("بِسْمِ اللَّهِ") == "اللَّهِ بِسْمِ"

    def test_hebrew(self):
        assert _do_reorder("שלום עולם") == "עולם שלום"


class TestDoReorderMixed:
    def test_rtl_base_with_english_suffix(self):
        assert _do_reorder("حبيبي (Remix)") == "(Remix) حبيبي"

    def test_ltr_base_with_arabic_suffix(self):
        assert _do_reorder("Beautiful Day - محمد حماقي") == "Beautiful Day - حماقي محمد"

    def test_rtl_base_with_embedded_english(self):
        assert _do_reorder("كلمات DJ Khaled أغنية") == "أغنية DJ Khaled كلمات"

    def test_rtl_base_feat(self):
        assert _do_reorder("فيروز feat. Rahbani") == "feat. Rahbani فيروز"

    def test_rtl_with_number(self):
        assert _do_reorder("أغنية رقم 3") == "3 رقم أغنية"

    def test_rtl_with_dash(self):
        assert _do_reorder("عمرو دياب - تملي معاك") == "معاك تملي - دياب عمرو"

    def test_ltr_base_keeps_ltr_order(self):
        assert _do_reorder("Song by فنان العرب is great") == "Song by العرب فنان is great"

    def test_multiple_ltr_blocks_in_rtl(self):
        assert _do_reorder("كلمة Hello كلمة World كلمة") == "كلمة World كلمة Hello كلمة"


class TestDoReorderEdgeCases:
    def test_arabic_with_parentheses(self):
        assert _do_reorder("أنشودة (رائعة)") == "(رائعة) أنشودة"

    def test_emoji_with_arabic(self):
        assert _do_reorder("🎵 أغنية جميلة") == "جميلة أغنية 🎵"

    def test_arabic_comma(self):
        assert _do_reorder("أحمد، محمد") == "محمد أحمد،"

    def test_arabic_question_mark(self):
        assert _do_reorder("ما هذا؟") == "هذا؟ ما"

    def test_empty_string(self):
        assert _do_reorder("") == ""

    def test_whitespace_only(self):
        assert _do_reorder("   ") == "   "

    def test_single_word(self):
        assert _do_reorder("مرحبا") == "مرحبا"


# ── isolate_bidi ─────────────────────────────────────────────────────


class TestIsolateBidi:
    """isolate_bidi wraps RTL-containing text in FSI...PDI to prevent
    BiDi bleed across visual chunks (table cells, playback bar fragments)."""

    def test_arabic_wrapped(self):
        assert isolate_bidi("مرحبا") == f"{FSI}مرحبا{PDI}"

    def test_hebrew_wrapped(self):
        assert isolate_bidi("שלום") == f"{FSI}שלום{PDI}"

    def test_pure_latin_unchanged_by_default(self):
        assert isolate_bidi("Hello") == "Hello"

    def test_pure_latin_wrapped_when_forced(self):
        assert isolate_bidi("Hello", only_if_rtl=False) == f"{FSI}Hello{PDI}"

    def test_empty_unchanged(self):
        assert isolate_bidi("") == ""

    def test_idempotent(self):
        once = isolate_bidi("مرحبا")
        twice = isolate_bidi(once)
        assert once == twice

    def test_mixed_content_wrapped(self):
        result = isolate_bidi("Song مرحبا")
        assert result.startswith(FSI)
        assert result.endswith(PDI)
        assert "مرحبا" in result

    def test_zero_cell_width_via_rich(self):
        """The contract: isolation marks must not consume display columns."""
        from rich.cells import cell_len

        plain = "مرحبا"
        wrapped = isolate_bidi(plain)
        assert cell_len(wrapped) == cell_len(plain)


# ── Render-site enforcement (regression guard) ───────────────────────


class TestIsolateBidiCallSites:
    """Verify that every render site that displays user-supplied text
    calls isolate_bidi.  This guards against re-introducing the BiDi
    bleed bug where Arabic titles appear duplicated at row edges or
    bleed into adjacent widgets in the playback bar.

    If you move or rename these render sites, update this test —
    do NOT just delete entries without ensuring isolation is preserved.
    """

    REQUIRED_SITES = {
        "src/ytm_player/ui/widgets/track_table.py": "isolate_bidi",
        "src/ytm_player/ui/playback_bar.py": "isolate_bidi",
        "src/ytm_player/ui/sidebars/lyrics_sidebar.py": "isolate_bidi",
    }

    def test_render_sites_call_isolate_bidi(self):
        import pathlib

        repo_root = pathlib.Path(__file__).parent.parent.parent
        for rel_path, token in self.REQUIRED_SITES.items():
            full_path = repo_root / rel_path
            assert full_path.exists(), f"{rel_path} does not exist"
            text = full_path.read_text(encoding="utf-8")
            assert token in text, (
                f"{rel_path} must call {token} to prevent RTL BiDi bleed. "
                "Wrap user text fragments (title, artist, album, lyrics) "
                "with isolate_bidi() AFTER truncate()."
            )
