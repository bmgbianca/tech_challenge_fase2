import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPORT_PERIODS_IN_DAYS = {"day": 1, "week": 7}

HISTORY_FILE = Path(__file__).resolve().parent.parent / "data" / "route_runs.json"


def _read_all():
    if not HISTORY_FILE.exists():
        return []

    with open(HISTORY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def _write_all(runs):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(runs, file, ensure_ascii=False, indent=2)


def save_route_run(
    *,
    population_type,
    population_size,
    mutation_probability,
    best_distance,
    total_duration,
    priorities_on_time,
    stops_count,
    vehicles_number,
    best_route,
    generations_run,
):
    """Appends one optimization run to the local JSON history file, so it
    can later be used (e.g. by an LLM) to compare routes over time.

    best_route holds one list of city names per vehicle. city_set is the
    sorted list of distinct cities of the run (the origin is repeated in
    every vehicle route, so it is deduplicated)."""

    run = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "population_type": population_type,
        "population_size": population_size,
        "mutation_probability": mutation_probability,
        "best_distance": best_distance,
        "total_duration": total_duration,
        "priorities_on_time": priorities_on_time,
        "stops_count": stops_count,
        "vehicles_number": vehicles_number,
        "best_route": best_route,
        "city_set": sorted({name for vehicle in best_route for name in vehicle}),
        "generations_run": generations_run,
    }

    runs = _read_all()
    runs.append(run)
    _write_all(runs)

    return run


def get_route_runs():
    return _read_all()


def filter_runs_by_period(runs, period, now=None):
    """Keeps only the runs created within the last day ("day") or the last
    7 days ("week"). "all" (or None) keeps every run. Raises ValueError for
    any other period."""

    if period in (None, "all"):
        return runs

    if period not in REPORT_PERIODS_IN_DAYS:
        raise ValueError("Período inválido. Use 'day', 'week' ou 'all'.")

    now = now or datetime.now(timezone.utc)
    start = now - timedelta(days=REPORT_PERIODS_IN_DAYS[period])

    return [run for run in runs if datetime.fromisoformat(run["created_at"]) >= start]
