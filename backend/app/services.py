import itertools
from typing import List

from ..config import (
    MAX_GENERATIONS,
    MIN_POPULATION_SIZE,
    MUTATION_PROBABILITY,
    PLATEAU_WINDOW,
    POPULATION_SIZE,
    VALID_POPULATION_TYPES,
)
from ..config.interfaces import CityEntity
from ..data import sao_paulo_cities
from ..ga import (
    calculate_critical_duration,
    calculate_fitness,
    calculate_routes,
    calculate_solution_duration,
    generate_initial_population,
    order_crossover,
    select_parents,
    segment_shuffle_mutation,
    sort_population_by_fitness,
)


def get_optimized_route(
    fixed_start_city_name="São Paulo",
    population_type="nearest_neighbor",
    population_size=POPULATION_SIZE,
    mutation_probability=MUTATION_PROBABILITY,
    max_generations=MAX_GENERATIONS,
    plateau_window=PLATEAU_WINDOW,
    cities: List[CityEntity] | None = sao_paulo_cities,
):
    """Runs the full GA loop (headless, no Pygame) and returns the final
    result plus periodic snapshots of the best route, for the frontend
    to animate as a replay."""

    if population_type not in VALID_POPULATION_TYPES:
        raise ValueError(f"population_type inválido: {population_type}")

    if population_size < MIN_POPULATION_SIZE:
        raise ValueError(f"population_size mínimo: {MIN_POPULATION_SIZE}")

    if not 0 <= mutation_probability <= 1:
        raise ValueError("mutation_probability ser um valor entre 0 e 1.")

    return run_genetic_algorithm(
        cities,
        fixed_start_city_name,
        population_type,
        population_size,
        mutation_probability,
        max_generations,
        plateau_window,
    )


def run_genetic_algorithm(
    cities=sao_paulo_cities,
    fixed_start_city_name="São Paulo",
    population_type="nearest_neighbor",
    population_size=POPULATION_SIZE,
    mutation_probability=MUTATION_PROBABILITY,
    max_generations=MAX_GENERATIONS,
    plateau_window=PLATEAU_WINDOW,
):
    calculated_routes = calculate_routes(cities)
    calculated_distances = calculated_routes["cities_distances"]
    calculated_durations = calculated_routes["cities_durations"]

    population = generate_initial_population(
        population_type,
        calculated_distances,
        population_size,
        cities,
        fixed_start_city_name,
    )

    generation_counter = itertools.count(start=1)
    best_fitness_values = []
    snapshots = []

    running = True
    while running:
        generation = next(generation_counter)

        population_with_fitness = [
            {
                "individual": individual,
                "total_distance": calculate_fitness(calculated_distances, individual),
                "critical_duration": calculate_critical_duration(
                    calculated_durations, individual
                ),
            }
            for individual in population
        ]

        sorted_population_with_fitness = sort_population_by_fitness(
            calculated_durations, population_with_fitness
        )

        best = sorted_population_with_fitness[0]
        second_best = sorted_population_with_fitness[1]
        best_fitness_values.append(best["total_distance"])

        snapshots.append(
            {
                "generation": generation,
                "best_distance": best["total_distance"],
                "best_duration": calculate_solution_duration(
                    calculated_durations, best["individual"]
                ),
                "critical_duration": best["critical_duration"],
                "route": [city["name"] for city in best["individual"]],
                "second_best_distance": second_best["total_distance"],
                "second_best_route": [
                    city["name"] for city in second_best["individual"]
                ],
            }
        )

        # ELITISM PRESERVES THE BEST 4 INDIVIDUALS IN A GENERATION:
        new_population = [
            sorted_population_with_fitness[0]["individual"],
            sorted_population_with_fitness[1]["individual"],
            sorted_population_with_fitness[2]["individual"],
            sorted_population_with_fitness[3]["individual"],
        ]

        while len(new_population) < population_size:
            parents = select_parents(calculated_durations, population_with_fitness)
            children = order_crossover(parents)
            child1 = segment_shuffle_mutation(children[0], mutation_probability, True)
            child2 = segment_shuffle_mutation(children[1], mutation_probability, True)
            new_population.append(child1)
            new_population.append(child2)

        population = new_population

        stability_reached = len(best_fitness_values) > plateau_window and all(
            value == best_fitness_values[-plateau_window]
            for value in best_fitness_values[-plateau_window:]
        )

        if len(best_fitness_values) >= max_generations or stability_reached:
            running = False

    final_best = sorted_population_with_fitness[0]
    final_second_best = sorted_population_with_fitness[1]
    total_duration = calculate_solution_duration(
        calculated_durations, final_best["individual"]
    )

    if snapshots[-1]["generation"] != generation:
        snapshots.append(
            {
                "generation": generation,
                "best_distance": final_best["total_distance"],
                "best_duration": total_duration,
                "critical_duration": final_best["critical_duration"],
                "route": [city["name"] for city in final_best["individual"]],
                "second_best_distance": final_second_best["total_distance"],
                "second_best_route": [
                    city["name"] for city in final_second_best["individual"]
                ],
            }
        )

    return {
        "calculated_routes": calculated_routes,
        "best_solution": final_best,
        "total_duration": total_duration,
        "fitness_history": best_fitness_values,
        "snapshots": snapshots,
    }
