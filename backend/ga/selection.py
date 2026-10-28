from functools import cmp_to_key
from typing import List, Tuple
import random

from ..config import CityEntity, Individual, Matrix, PopulationFitness
from ..config import TIME_LIMIT

from .calculation import calculate_solution_duration


def sort_population_by_fitness(
    duration_matrix: Matrix,
    population_fitness: List[Tuple[List[CityEntity], float]],
) -> List[Tuple[List[CityEntity], float]]:

    def sort_function(a, b):
        solution_a = a["individual"]
        solution_b = b["individual"]

        a_is_valid = is_solution_valid(duration_matrix, solution_a)
        b_is_valid = is_solution_valid(duration_matrix, solution_b)
        minimum_distance_solution = min([a, b], key=lambda x: x["total_distance"])

        if a_is_valid and b_is_valid:
            if a == minimum_distance_solution:
                return -1
            else:
                return 1
        elif a_is_valid:
            return -1
        elif b_is_valid:
            return 1
        else:
            if b == select_best_invalid_solution(duration_matrix, [a, b]):
                return 1
            else:
                return -1

    return sorted(population_fitness, key=cmp_to_key(sort_function))


def select_parents(
    duration_matrix: Matrix,
    population_fitness: PopulationFitness,
) -> List[Individual]:

    parent1_contestants = random.choices(population_fitness, k=2)
    parent2_contestants = random.choices(population_fitness, k=2)

    parent1 = select_winner_solution(duration_matrix, parent1_contestants)
    parent2 = select_winner_solution(duration_matrix, parent2_contestants)

    return [parent1["individual"], parent2["individual"]]


def select_winner_solution(
    duration_matrix: Matrix,
    solutions: PopulationFitness,
) -> dict[str, Individual | float]:
    solution1 = solutions[0]
    solution2 = solutions[1]

    solution1_is_valid = is_solution_valid(duration_matrix, solution1["individual"])
    solution2_is_valid = is_solution_valid(duration_matrix, solution2["individual"])

    if solution1_is_valid and solution2_is_valid:
        return min(solutions, key=lambda x: x["total_distance"])
    elif solution1_is_valid:
        return solution1
    elif solution2_is_valid:
        return solution2
    else:
        return select_best_invalid_solution(duration_matrix, solutions)


def is_solution_valid(
    duration_matrix: Matrix,
    solution: Individual,
):
    is_there_any_priority_delivery = any(
        city.get("priority") == True for city in solution
    )

    if not is_there_any_priority_delivery:
        return True

    priority_cities_indices = [
        index for index, city in enumerate(solution) if city.get("priority") == True
    ]

    """
    Selects only the part of the route until last visited priority
    city and calculates the duration of this part of the route:
    """
    solution_until_last_priority = solution[: (max(priority_cities_indices) + 1)]
    duration = calculate_solution_duration(
        duration_matrix, solution_until_last_priority
    )

    # If duration exceeds time constraints, the solution isn't valid
    if duration > TIME_LIMIT:
        return False

    return True


def select_best_invalid_solution(
    duration_matrix: Matrix,
    solutions: PopulationFitness,
) -> dict[str, Individual | float]:

    priority_deliveries = any(
        city.get("priority") == True for city in solutions[0]["individual"]
    )

    if not priority_deliveries:
        return min(solutions, key=lambda x: x["total_distance"])

    solutions_data = [
        {
            "solution": solutions[0],
            "route_duration_until_last_priority": 0,
            "valid_priority_routes_count": 0,
        },
        {
            "solution": solutions[1],
            "route_duration_until_last_priority": 0,
            "valid_priority_routes_count": 0,
        },
    ]

    for index, solution in enumerate(solutions):
        solution_route = solution["individual"]

        priority_cities_indices = [
            index
            for index, city in enumerate(solution_route)
            if city.get("priority") == True
        ]

        route_duration_until_last_priority = calculate_solution_duration(
            duration_matrix, solution_route[: (max(priority_cities_indices) + 1)]
        )
        solutions_data[index][
            "route_duration_until_last_priority"
        ] = route_duration_until_last_priority

        """ A list of booleans, where True represents that the route
        comes to current prioriry city on time, and False represents
        that the route cannot make it on time
        """
        priority_routes_validation = []

        for i in priority_cities_indices:
            route_until_priority_city = solution_route[: (i + 1)]
            route_duration = calculate_solution_duration(
                duration_matrix, route_until_priority_city
            )

            if route_duration <= TIME_LIMIT:
                priority_routes_validation.append(True)
            else:
                priority_routes_validation.append(False)

        true_validations = filter(lambda x: x == True, priority_routes_validation)
        true_validations_list = list(true_validations)

        """Key 'valid_priority_routes_count' shows how many priority
        cities were visited on time for the current solution
        """
        solutions_data[index]["valid_priority_routes_count"] = len(
            true_validations_list
        )

    if (
        solutions_data[0]["valid_priority_routes_count"]
        > solutions_data[1]["valid_priority_routes_count"]
    ):
        return solutions_data[0]["solution"]
    elif (
        solutions_data[0]["valid_priority_routes_count"]
        < solutions_data[1]["valid_priority_routes_count"]
    ):
        return solutions_data[1]["solution"]
    else:
        best_solution_data = min(
            solutions_data,
            key=lambda x: x["route_duration_until_last_priority"],
        )
        return best_solution_data["solution"]
