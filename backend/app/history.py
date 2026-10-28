import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

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
    critical_duration,
    stops_count,
    best_route,
    generations_run,
):
    """Appends one optimization run to the local JSON history file, so it
    can later be used (e.g. by an LLM) to compare routes over time."""

    run = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "population_type": population_type,
        "population_size": population_size,
        "mutation_probability": mutation_probability,
        "best_distance": best_distance,
        "total_duration": total_duration,
        "critical_duration": critical_duration,
        "stops_count": stops_count,
        "best_route": best_route,
        "city_set": sorted(best_route),
        "generations_run": generations_run,
    }

    runs = _read_all()
    runs.append(run)
    _write_all(runs)

    return run


def get_route_runs():
    return _read_all()
