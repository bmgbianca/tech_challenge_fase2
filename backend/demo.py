"""Headless demonstration of the genetic algorithm (no Pygame, no web app,
no LLM): runs the open-route VRP over the fixed 16 cities of
backend/data/route_cities.py and prints the routes of every vehicle.

    python -m backend.demo
    python -m backend.demo --strategy cheapest_insertion --vehicles 2 --seed 7

The distance/duration matrix is requested to OpenRouteService only once and
then kept in backend/data/demo_routes.json, so later runs (and the notebook
in notebooks/demo.ipynb) work offline and spend no API quota.
"""

import argparse
import json
import os
import random
import time
from pathlib import Path

from dotenv import load_dotenv

# The OpenRouteService key is only needed when the matrix is not cached yet,
# but the client module reads it on import (load_dotenv does not override
# variables that are already set, so the real key must be loaded first):
load_dotenv(Path(__file__).resolve().parent / ".env")
os.environ.setdefault("OPENROUTESERVICE_API_KEY", "offline-demo")

from .app.services import get_routes_names, run_genetic_algorithm  # noqa: E402
from .constants import (  # noqa: E402
    MUTATION_PROBABILITY,
    ORIGIN,
    VALID_POPULATION_TYPES,
    VEHICLES_NUMBER,
)
from .data import sao_paulo_cities  # noqa: E402
from .ga import (  # noqa: E402
    calculate_fitness,
    calculate_routes,
    calculate_solution_duration,
)
from .helpers import convert_seconds  # noqa: E402
from .models import RunGeneticAlgorithmArgs  # noqa: E402

DEMO_ROUTES_FILE = Path(__file__).resolve().parent / "data" / "demo_routes.json"

# Smaller than the web app defaults, so the demo finishes in seconds:
DEMO_POPULATION_SIZE = 200
DEMO_MAX_GENERATIONS = 500
DEMO_PLATEAU_WINDOW = 100
DEMO_SEED = 42


def _serialize_matrix(matrix):
    return {f"{first}-{second}": value for (first, second), value in matrix.items()}


def _deserialize_matrix(matrix):
    return {
        tuple(int(city_id) for city_id in key.split("-")): value
        for key, value in matrix.items()
    }


def _restrict_matrix(matrix, ids):
    return {pair: value for pair, value in matrix.items() if set(pair) <= ids}


def load_demo_routes(
    cities=None, cache_file=DEMO_ROUTES_FILE, dataset=sao_paulo_cities
):
    """Distance and duration matrices of the given cities (default: the whole
    dataset). The cache always holds the whole dataset, so any subset of it is
    served from the cache too. When the cache is missing or was built for other
    coordinates, the dataset's matrices are requested to OpenRouteService (needs
    OPENROUTESERVICE_API_KEY) and cached."""

    cities = dataset if cities is None else cities
    coordinates = [city["coordinates"] for city in dataset]
    cached = None

    if cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        if cached["coordinates"] != coordinates:
            cached = None

    if cached is None:
        if os.environ["OPENROUTESERVICE_API_KEY"] == "offline-demo":
            raise RuntimeError(
                "Matriz de distâncias não encontrada em cache. Defina "
                "OPENROUTESERVICE_API_KEY em backend/.env para gerá-la."
            )

        routes = calculate_routes(dataset)
        cached = {
            "coordinates": coordinates,
            "cities_distances": _serialize_matrix(routes["cities_distances"]),
            "cities_durations": _serialize_matrix(routes["cities_durations"]),
        }
        cache_file.write_text(json.dumps(cached, ensure_ascii=False), encoding="utf-8")

    ids = {city["id"] for city in cities}
    return {
        "cities_distances": _restrict_matrix(
            _deserialize_matrix(cached["cities_distances"]), ids
        ),
        "cities_durations": _restrict_matrix(
            _deserialize_matrix(cached["cities_durations"]), ids
        ),
    }


def run_demo(
    strategy="nearest_neighbor",
    vehicles_number=VEHICLES_NUMBER,
    population_size=DEMO_POPULATION_SIZE,
    mutation_probability=MUTATION_PROBABILITY,
    max_generations=DEMO_MAX_GENERATIONS,
    plateau_window=DEMO_PLATEAU_WINDOW,
    seed=DEMO_SEED,
    cities=sao_paulo_cities,
    origin=ORIGIN,
):
    """Runs the genetic algorithm with the cached matrices. The seed makes the
    result reproducible. Returns the algorithm result plus "seconds" (how long
    it took) and the parameters used."""

    random.seed(seed)
    routes = load_demo_routes(cities)

    started_at = time.perf_counter()
    result = run_genetic_algorithm(
        RunGeneticAlgorithmArgs(
            origin_city=origin,
            cities=cities,
            population_type=strategy,
            population_size=population_size,
            mutation_probability=mutation_probability,
            max_generations=max_generations,
            plateau_window=plateau_window,
            vehicles_number=vehicles_number,
            calculated_routes=routes,
        )
    )
    result["seconds"] = time.perf_counter() - started_at
    result["parameters"] = {
        "strategy": strategy,
        "vehicles_number": vehicles_number,
        "population_size": population_size,
        "mutation_probability": mutation_probability,
        "seed": seed,
    }
    return result


def format_duration(seconds):
    hours, minutes = convert_seconds(seconds)
    return f"{int(hours)}h{int(minutes):02d}min"


def vehicle_summaries(result):
    """One dict per vehicle: route (city names), distance in km and duration."""

    routes = result["calculated_routes"]
    distances, durations = routes["cities_distances"], routes["cities_durations"]

    return [
        {
            "route": route_names,
            "distance_km": calculate_fitness(distances, [vehicle]),
            "duration_seconds": calculate_solution_duration(durations, [vehicle]),
        }
        for vehicle, route_names in zip(
            result["best_solution"]["individual"],
            get_routes_names(result["best_solution"]["individual"]),
        )
    ]


def format_summary(result):
    solution = result["best_solution"]
    parameters = result["parameters"]
    lines = [
        f"Estratégia: {parameters['strategy']} | veículos: "
        f"{parameters['vehicles_number']} | população: "
        f"{parameters['population_size']} | semente: {parameters['seed']}",
        f"Gerações: {len(result['fitness_history'])} "
        f"({result['seconds']:.1f}s)",
        "",
    ]

    for number, vehicle in enumerate(vehicle_summaries(result), start=1):
        lines.append(
            f"Veículo {number} — {vehicle['distance_km']:.1f} km, "
            f"{format_duration(vehicle['duration_seconds'])}"
        )
        lines.append("  " + " → ".join(vehicle["route"]))

    lines += [
        "",
        f"Distância total: {solution['total_distance']:.1f} km",
        f"Duração da solução (veículo mais demorado): "
        f"{format_duration(result['total_duration'])}",
        "Prioridades dentro do prazo: "
        + ("sim" if solution["priorities_on_time"] else "NÃO"),
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Demonstração do algoritmo genético para o VRP (sem interface)."
    )
    parser.add_argument(
        "--strategy",
        choices=sorted(VALID_POPULATION_TYPES),
        default="nearest_neighbor",
        help="estratégia da população inicial",
    )
    parser.add_argument("--vehicles", type=int, default=VEHICLES_NUMBER)
    parser.add_argument("--population", type=int, default=DEMO_POPULATION_SIZE)
    parser.add_argument("--seed", type=int, default=DEMO_SEED)
    args = parser.parse_args()

    result = run_demo(
        strategy=args.strategy,
        vehicles_number=args.vehicles,
        population_size=args.population,
        seed=args.seed,
    )
    print(format_summary(result))


if __name__ == "__main__":
    main()
