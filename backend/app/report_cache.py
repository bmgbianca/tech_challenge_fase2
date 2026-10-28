import json
from datetime import datetime, timezone
from pathlib import Path

CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "comparative_reports.json"


def _read_all():
    if not CACHE_FILE.exists():
        return {}

    with open(CACHE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def _write_all(cache):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as file:
        json.dump(cache, file, ensure_ascii=False, indent=2)


def build_cache_key(run_ids):
    """The cache key is the exact set of run IDs that fed the report. If a
    new optimization run is added for the same city set, the key changes
    and a fresh report is generated — otherwise, the same key always
    returns the previously generated report, never calling the LLM twice
    for the same data."""

    return "|".join(sorted(run_ids))


def get_cached_report(cache_key):
    cache = _read_all()
    return cache.get(cache_key)


def save_report(cache_key, report, run_ids):
    cache = _read_all()
    cache[cache_key] = {
        "report": report,
        "run_ids": sorted(run_ids),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_all(cache)
