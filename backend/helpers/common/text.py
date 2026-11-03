import unicodedata


def normalize_text(text: str) -> str:
    """Lowercases the text and removes its accents, so that searches ignore
    both (e.g. "São Paulo" and "sao paulo" become the same string)."""
    decomposed = unicodedata.normalize("NFD", text)
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return without_accents.casefold()
