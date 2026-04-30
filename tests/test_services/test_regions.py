"""Tests for the YouTube Music chart-region list."""

from __future__ import annotations


class TestChartRegions:
    def test_module_imports(self):
        from ytm_player.services import regions

        assert hasattr(regions, "CHART_REGIONS")

    def test_regions_is_tuple_of_pairs(self):
        from ytm_player.services.regions import CHART_REGIONS

        assert isinstance(CHART_REGIONS, tuple)
        assert all(isinstance(item, tuple) and len(item) == 2 for item in CHART_REGIONS)

    def test_codes_are_uppercase_2char(self):
        from ytm_player.services.regions import CHART_REGIONS

        for code, name in CHART_REGIONS:
            assert isinstance(code, str)
            assert isinstance(name, str)
            assert code.isupper(), f"non-uppercase code: {code!r}"
            assert len(code) == 2, f"non-2-char code: {code!r}"

    def test_names_non_empty(self):
        from ytm_player.services.regions import CHART_REGIONS

        for code, name in CHART_REGIONS:
            assert name.strip(), f"empty name for code {code!r}"

    def test_no_duplicate_codes(self):
        from ytm_player.services.regions import CHART_REGIONS

        codes = [c for c, _ in CHART_REGIONS]
        assert len(codes) == len(set(codes)), "duplicate codes present"

    def test_global_zz_present(self):
        """ZZ is YouTube Music's global / no-region marker; must be selectable."""
        from ytm_player.services.regions import CHART_REGIONS

        codes = [c for c, _ in CHART_REGIONS]
        assert "ZZ" in codes

    def test_us_present(self):
        """US is the default region in settings; must always be available."""
        from ytm_player.services.regions import CHART_REGIONS

        codes = [c for c, _ in CHART_REGIONS]
        assert "US" in codes

    def test_alphabetical_by_name(self):
        """ZZ first as special, remaining sorted alphabetically by display name."""
        from ytm_player.services.regions import CHART_REGIONS

        assert CHART_REGIONS[0][0] == "ZZ"
        rest = CHART_REGIONS[1:]
        names = [name for _, name in rest]
        assert names == sorted(names), "regions not alphabetical by name"

    def test_minimum_size(self):
        """At least 30 regions covering major markets."""
        from ytm_player.services.regions import CHART_REGIONS

        assert len(CHART_REGIONS) >= 30
