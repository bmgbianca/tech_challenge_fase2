from unittest.mock import patch

import pytest

from backend.app import report_cache


@pytest.fixture
def cache_file(tmp_path):
    file = tmp_path / "comparative_reports.json"
    with patch.object(report_cache, "CACHE_FILE", file):
        yield file


class TestBuildCacheKey:
    def test_does_not_depend_on_the_order_of_the_ids(self):
        assert report_cache.build_cache_key(["b", "a", "c"]) == "a|b|c"
        assert report_cache.build_cache_key(["c", "a", "b"]) == "a|b|c"

    def test_accepts_a_generator(self):
        assert report_cache.build_cache_key(i for i in ["y", "x"]) == "x|y"

    def test_different_sets_of_runs_have_different_keys(self):
        assert report_cache.build_cache_key(["a"]) != report_cache.build_cache_key(
            ["a", "b"]
        )


class TestReportCache:
    def test_returns_none_when_the_cache_file_does_not_exist(self, cache_file):
        assert report_cache.get_cached_report("qualquer") is None

    def test_saved_report_can_be_read_back(self, cache_file):
        report_cache.save_report("a|b", "texto", ["b", "a"])

        cached = report_cache.get_cached_report("a|b")

        assert cached["report"] == "texto"
        assert cached["run_ids"] == ["a", "b"]
        assert "generated_at" in cached

    def test_unknown_key_returns_none(self, cache_file):
        report_cache.save_report("a", "texto", ["a"])

        assert report_cache.get_cached_report("outra") is None

    def test_saving_keeps_the_other_reports(self, cache_file):
        report_cache.save_report("a", "primeiro", ["a"])
        report_cache.save_report("b", "segundo", ["b"])

        assert report_cache.get_cached_report("a")["report"] == "primeiro"
        assert report_cache.get_cached_report("b")["report"] == "segundo"

    def test_saving_the_same_key_replaces_the_report(self, cache_file):
        report_cache.save_report("a", "antigo", ["a"])
        report_cache.save_report("a", "novo", ["a"])

        assert report_cache.get_cached_report("a")["report"] == "novo"

    def test_keeps_accented_text_readable_in_the_file(self, cache_file):
        report_cache.save_report("a", "distância", ["a"])

        assert "distância" in cache_file.read_text(encoding="utf-8")

