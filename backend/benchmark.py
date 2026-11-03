"""Compares the genetic algorithm with other routing approaches and saves the
numbers in backend/data/benchmark_results.json (used by the technical report
and by notebooks/demo.ipynb).

    python -m backend.benchmark                 # GA, greedy, random search, exhaustive
    pip install ortools && python -m backend.benchmark --ortools   # + OR-Tools
    python -m backend.benchmark --only-ortools  # keeps the saved numbers, refreshes OR-Tools

Uses the cached distance matrix (backend/data/demo_routes.json), so it runs
offline. OR-Tools is optional and is not in requirements.txt.
"""

import argparse
import json
import random
import statistics
import time
from pathlib import Path

from .baselines import (
    best_of_population,
    best_of_random,
    evaluate,
    exhaustive_search,
    greedy_nearest_neighbor,
)
from .constants import TIME_LIMIT
from .data import sao_paulo_cities
from .demo import load_demo_routes, run_demo
from .ga import InitialPopulationArgs, generate_initial_population
from .helpers.domain import get_cities_distribution

RESULTS_FILE = Path(__file__).resolve().parent / "data" / "benchmark_results.json"
ORIGIN = "São Paulo"
VEHICLES = 3
SEEDS = list(range(1, 11))

# 8 destinations (3 priority cities) + the origin: small enough to try every solution
SMALL_NAMES = [
    "São Paulo", "Campinas", "Caraguatatuba", "Ribeirão Preto", "Bauru",
    "São Carlos", "Taubaté", "Bragança Paulista", "Franca",
]


def summarize(values):
    return {
        "mean": statistics.mean(values),
        "min": min(values),
        "max": max(values),
        "stdev": statistics.pstdev(values),
    }


def timed(function):
    started_at = time.perf_counter()
    result = function()
    return result, time.perf_counter() - started_at


def run_method(name, runs):
    """runs: list of (metrics dict, seconds). Aggregates the numbers."""

    return {
        "method": name,
        "runs": len(runs),
        "distance_km": summarize([metrics["distance_km"] for metrics, _ in runs]),
        "duration_seconds": summarize([m["duration_seconds"] for m, _ in runs]),
        "seconds": statistics.mean(seconds for _, seconds in runs),
        "valid_runs": sum(m["priorities_on_time"] for m, _ in runs),
    }


def ga_runs(strategy, seeds, **kwargs):
    runs, evaluations = [], []
    for seed in seeds:
        result = run_demo(strategy=strategy, vehicles_number=VEHICLES, seed=seed, **kwargs)
        routes = result["calculated_routes"]
        metrics = evaluate(routes, result["best_solution"]["individual"])
        runs.append((metrics, result["seconds"]))
        evaluations.append(
            len(result["fitness_history"]) * result["parameters"]["population_size"]
        )
    return runs, statistics.mean(evaluations)


def full_instance():
    routes = load_demo_routes()
    cities = sao_paulo_cities
    results = []

    ga_demo, budget = ga_runs("nearest_neighbor", SEEDS)
    ga_web, web_budget = ga_runs(
        "nearest_neighbor", SEEDS[:5], population_size=1000,
        max_generations=3000, plateau_window=500,
    )
    ga_random, _ = ga_runs("random", SEEDS)
    budget = int(budget)

    def one(function):
        def timed_run(seed):
            random.seed(seed)
            individual, seconds = timed(function)
            return evaluate(routes, individual), seconds
        return [timed_run(seed) for seed in SEEDS]

    results.append(run_method("AG (população 200, vizinho mais próximo)", ga_demo))
    results.append(run_method("AG (população 200, aleatória)", ga_random))
    results.append(run_method("AG (população 1000, parâmetros do app web)", ga_web))
    results.append(run_method(
        f"Busca aleatória ({budget} soluções)",
        one(lambda: best_of_random(routes, cities, ORIGIN, VEHICLES, budget)),
    ))
    results.append(run_method(
        "Vizinho mais próximo guloso (sem busca)",
        one(lambda: greedy_nearest_neighbor(routes, cities, ORIGIN, VEHICLES)),
    ))
    results.append(run_method(
        "Inserção mais barata (melhor de 200 construções)",
        one(lambda: best_of_population(routes, generate_initial_population(
            InitialPopulationArgs(
                population_strategy="cheapest_insertion",
                distances_matrix=routes["cities_distances"], population_size=200,
                cities=cities, origin_city_name=ORIGIN, vehicles_number=VEHICLES,
            )))),
    ))
    return results, {"ga_evaluations": budget, "ga_web_evaluations": int(web_budget)}


def small_instance():
    routes = load_demo_routes()
    cities = [city for city in sao_paulo_cities if city["name"] in SMALL_NAMES]
    vehicles = 2

    (balanced, tried_balanced), seconds_balanced = timed(
        lambda: exhaustive_search(routes, cities, ORIGIN, vehicles, balanced=True)
    )
    (free, tried_free), seconds_free = timed(
        lambda: exhaustive_search(routes, cities, ORIGIN, vehicles, balanced=False)
    )

    optimum = evaluate(routes, balanced)
    ga = []
    for seed in SEEDS:
        random.seed(seed)
        result = run_demo(
            strategy="nearest_neighbor", vehicles_number=vehicles, seed=seed,
            cities=cities, origin=ORIGIN,
        )
        ga.append(result["best_solution"]["total_distance"])

    hits = sum(abs(distance - optimum["distance_km"]) < 1e-6 for distance in ga)
    return {
        "cities": len(cities) - 1,
        "vehicles": vehicles,
        "balanced_optimum": optimum,
        "balanced_solutions_tried": tried_balanced,
        "balanced_seconds": seconds_balanced,
        "free_optimum": evaluate(routes, free),
        "free_solutions_tried": tried_free,
        "free_seconds": seconds_free,
        "ga_distances": ga,
        "ga_found_optimum": hits,
        "ga_gap_percent_mean": (statistics.mean(ga) / optimum["distance_km"] - 1) * 100,
    }


def solve_with_ortools(routes, cities, balanced, time_limit_seconds=10):
    """Open-route VRP with OR-Tools: a dummy end node at distance 0 from every
    city lets each vehicle end wherever it wants; priority cities must be
    reached within the deadline; every vehicle visits at least one city, and
    exactly its share when balanced=True."""

    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    ids = [city["id"] for city in cities]
    origin_index = next(i for i, city in enumerate(cities) if city["name"] == ORIGIN)
    count = len(cities)
    dummy = count
    per_vehicle, remainder = get_cities_distribution(cities, True, VEHICLES)
    shares = [per_vehicle + (1 if v < remainder else 0) for v in range(VEHICLES)]

    manager = pywrapcp.RoutingIndexManager(count + 1, VEHICLES, [origin_index] * VEHICLES, [dummy] * VEHICLES)
    routing = pywrapcp.RoutingModel(manager)

    def matrix_callback(matrix, scale):
        def callback(from_index, to_index):
            a, b = manager.IndexToNode(from_index), manager.IndexToNode(to_index)
            if a == dummy or b == dummy or a == b:
                return 0
            return int(matrix[(ids[a], ids[b])] * scale)
        return routing.RegisterTransitCallback(callback)

    distance_callback = matrix_callback(routes["cities_distances"], 100)
    routing.SetArcCostEvaluatorOfAllVehicles(distance_callback)

    routing.AddDimension(matrix_callback(routes["cities_durations"], 1), 0, 10**7, True, "time")
    time_dimension = routing.GetDimensionOrDie("time")
    for node, city in enumerate(cities):
        if city["priority"]:
            time_dimension.CumulVar(manager.NodeToIndex(node)).SetRange(0, TIME_LIMIT)

    def visit_count(from_index):
        node = manager.IndexToNode(from_index)
        return 0 if node in (origin_index, dummy) else 1

    routing.AddDimension(routing.RegisterUnaryTransitCallback(visit_count), 0, count, True, "count")
    count_dimension = routing.GetDimensionOrDie("count")
    for vehicle in range(VEHICLES):
        end = count_dimension.CumulVar(routing.End(vehicle))
        end.SetRange(*( (shares[vehicle], shares[vehicle]) if balanced else (1, count) ))

    parameters = pywrapcp.DefaultRoutingSearchParameters()
    parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    parameters.time_limit.seconds = time_limit_seconds

    solution, seconds = timed(lambda: routing.SolveWithParameters(parameters))
    individual = []
    for vehicle in range(VEHICLES):
        index, route = routing.Start(vehicle), []
        while not routing.IsEnd(index):
            route.append(cities[manager.IndexToNode(index)])
            index = solution.Value(routing.NextVar(index))
        individual.append(route)
    return individual, seconds


def ortools_rows():
    routes = load_demo_routes()
    rows = []
    for balanced, name in [
        (True, "OR-Tools (mesma divisão de cidades por veículo do AG)"),
        (False, "OR-Tools (divisão livre das cidades)"),
    ]:
        individual, seconds = solve_with_ortools(routes, sao_paulo_cities, balanced)
        metrics = evaluate(routes, individual)
        rows.append(run_method(name, [(metrics, seconds)]) | {
            "routes": [[city["name"] for city in vehicle] for vehicle in individual],
            "sizes": [len(vehicle) - 1 for vehicle in individual],
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ortools", action="store_true", help="inclui o OR-Tools (pip install ortools)")
    parser.add_argument("--only-ortools", action="store_true", help="só atualiza as linhas do OR-Tools no arquivo salvo")
    args = parser.parse_args()

    if args.only_ortools:
        results = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
        methods = [m for m in results["methods"] if not m["method"].startswith("OR-Tools")]
        methods += ortools_rows()
        results["methods"] = methods
    else:
        methods, budgets = full_instance()
        if args.ortools:
            methods += ortools_rows()

        results = {
            "instance": {"cities": len(sao_paulo_cities) - 1, "vehicles": VEHICLES, "origin": ORIGIN,
                         "deadline_seconds": TIME_LIMIT, "seeds": len(SEEDS)},
            "budgets": budgets,
            "methods": methods,
            "small_instance": small_instance(),
        }
    RESULTS_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    for row in methods:
        print(f"{row['method']:<58} {row['distance_km']['mean']:>8.1f} km "
              f"(min {row['distance_km']['min']:.1f}, max {row['distance_km']['max']:.1f}) "
              f"{row['seconds']:>6.1f}s válidas {row['valid_runs']}/{row['runs']}")
    small = results["small_instance"]
    print("\nInstância pequena:", {k: v for k, v in small.items() if k != "ga_distances"})


if __name__ == "__main__":
    main()
