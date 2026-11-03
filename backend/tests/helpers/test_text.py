import pytest

from backend.helpers import normalize_text


class TestNormalizeText:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("São Paulo", "sao paulo"),
            ("SÃO PAULO", "sao paulo"),
            ("Araçatuba", "aracatuba"),
            ("Bragança Paulista", "braganca paulista"),
            ("Ribeirão Preto", "ribeirao preto"),
            ("Campinas", "campinas"),
            ("", ""),
        ],
    )
    def test_removes_accents_and_lowercases(self, text, expected):
        assert normalize_text(text) == expected

    def test_text_with_and_without_accents_match(self):
        assert normalize_text("São José dos Campos") == normalize_text(
            "sao jose dos campos"
        )

    def test_already_decomposed_accents_are_removed_too(self):
        assert normalize_text("São Paulo") == "sao paulo"
