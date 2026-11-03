from typing import List

from ..helpers import convert_seconds


def _percentage(part: float, whole: float) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


def calculate_runs_metrics(runs: List[dict]) -> dict:
    """Aggregates distance and duration of the given stored runs, so the LLM
    only has to interpret ready-made numbers instead of doing the math.

    "Savings" is how much the best run (shortest distance / duration)
    saves compared to the worst one and to the average of the runs."""

    distances = [run["best_distance"] for run in runs]
    durations = [run["total_duration"] for run in runs]

    best_distance, worst_distance = min(distances), max(distances)
    average_distance = sum(distances) / len(distances)
    best_duration, worst_duration = min(durations), max(durations)
    average_duration = sum(durations) / len(durations)

    return {
        "runs_count": len(runs),
        "distance_km": {
            "best": round(best_distance, 1),
            "worst": round(worst_distance, 1),
            "average": round(average_distance, 1),
            "savings_vs_worst_km": round(worst_distance - best_distance, 1),
            "savings_vs_worst_percent": _percentage(
                worst_distance - best_distance, worst_distance
            ),
            "savings_vs_average_percent": _percentage(
                average_distance - best_distance, average_distance
            ),
        },
        "duration": {
            "best": convert_seconds(best_duration),
            "worst": convert_seconds(worst_duration),
            "average": convert_seconds(average_duration),
            "savings_vs_worst": convert_seconds(worst_duration - best_duration),
            "savings_vs_worst_percent": _percentage(
                worst_duration - best_duration, worst_duration
            ),
            "savings_vs_average_percent": _percentage(
                average_duration - best_duration, average_duration
            ),
        },
    }
