import itertools

from ..constants import (
    MIN_POPULATION_SIZE,
    TIME_LIMIT,
    VALID_POPULATION_TYPES,
)
from ..models import (
    Individual,
    GetOptimizedRouteArgs,
    RunGeneticAlgorithmArgs,
    SelectParentsArgs,
    SortPopulationByFitnessArgs,
)

from ..ga import (
    are_priorities_on_time,
    calculate_fitness,
    calculate_routes,
    calculate_solution_duration,
    generate_initial_population,
    InitialPopulationArgs,
    order_crossover,
    select_parents,
    segment_shuffle_mutation,
    sort_population_by_fitness,
)


def get_routes_names(individual: Individual) -> list[list[str]]:
    """Converts an individual into what is stored in the snapshots: one list
    of city names per vehicle, e.g. [["A", "B", "C"], ["A", "D"]]."""
    return [[city["name"] for city in vehicle] for vehicle in individual]


def get_optimized_route(arg: GetOptimizedRouteArgs):
    """Runs the full GA loop (headless, no Pygame) and returns the final
    result plus periodic snapshots of the best route, for the frontend
    to animate as a replay."""

    if arg.population_type not in VALID_POPULATION_TYPES:
        raise ValueError(f"population_type inválido: {arg.population_type}")

    if arg.population_size < MIN_POPULATION_SIZE:
        raise ValueError(f"population_size mínimo: {MIN_POPULATION_SIZE}")

    if not 0 <= arg.mutation_probability <= 1:
        raise ValueError("mutation_probability deve ser um valor entre 0 e 1.")

    return run_genetic_algorithm(
        RunGeneticAlgorithmArgs(
            cities=arg.cities,
            origin_city=arg.origin_city,
            population_type=arg.population_type,
            population_size=arg.population_size,
            mutation_probability=arg.mutation_probability,
            max_generations=arg.max_generations,
            plateau_window=arg.plateau_window,
            vehicles_number=arg.vehicles_number,
        )
    )


def run_genetic_algorithm(arg: RunGeneticAlgorithmArgs):
    calculated_routes = calculate_routes(arg.cities)
    calculated_distances = calculated_routes["cities_distances"]
    calculated_durations = calculated_routes["cities_durations"]

    population = generate_initial_population(
        InitialPopulationArgs(
            population_strategy=arg.population_type,
            distances_matrix=calculated_distances,
            population_size=arg.population_size,
            cities=arg.cities,
            origin_city_name=arg.origin_city,
            vehicles_number=arg.vehicles_number,
        )
    )

    # Without a fixed origin, no city is repeated at the start of every vehicle:
    is_origin = bool(arg.origin_city)

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
                "priorities_on_time": are_priorities_on_time(
                    calculated_durations, individual, TIME_LIMIT
                ),
            }
            for individual in population
        ]

        sorted_population_with_fitness = sort_population_by_fitness(
            SortPopulationByFitnessArgs(
                duration_matrix=calculated_durations,
                population_fitness=population_with_fitness,
            )
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
                "priorities_on_time": best["priorities_on_time"],
                "route": get_routes_names(best["individual"]),
                "second_best_distance": second_best["total_distance"],
                "second_best_route": get_routes_names(second_best["individual"]),
            }
        )

        # ELITISM PRESERVES THE BEST 4 INDIVIDUALS IN A GENERATION:
        new_population = [
            sorted_population_with_fitness[0]["individual"],
            sorted_population_with_fitness[1]["individual"],
            sorted_population_with_fitness[2]["individual"],
            sorted_population_with_fitness[3]["individual"],
        ]

        while len(new_population) < arg.population_size:
            parents = select_parents(
                SelectParentsArgs(
                    duration_matrix=calculated_durations,
                    population_fitness=population_with_fitness,
                )
            )
            children = order_crossover({"parents": parents, "is_origin": is_origin})
            child1 = segment_shuffle_mutation(
                {
                    "individual": children[0],
                    "mutation_probability": arg.mutation_probability,
                    "is_origin": is_origin,
                }
            )
            child2 = segment_shuffle_mutation(
                {
                    "individual": children[1],
                    "mutation_probability": arg.mutation_probability,
                    "is_origin": is_origin,
                }
            )
            new_population.append(child1)
            new_population.append(child2)

        population = new_population

        stability_reached = len(best_fitness_values) > arg.plateau_window and all(
            value == best_fitness_values[-arg.plateau_window]
            for value in best_fitness_values[-arg.plateau_window :]
        )

        if len(best_fitness_values) >= arg.max_generations or stability_reached:
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
                "priorities_on_time": final_best["priorities_on_time"],
                "route": get_routes_names(final_best["individual"]),
                "second_best_distance": final_second_best["total_distance"],
                "second_best_route": get_routes_names(final_second_best["individual"]),
            }
        )

    return {
        "calculated_routes": calculated_routes,
        "best_solution": final_best,
        "total_duration": total_duration,
        "fitness_history": best_fitness_values,
        "snapshots": snapshots,
    }
