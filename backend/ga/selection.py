from functools import cmp_to_key
from typing import List
import random

from ..models import (
    Individual,
    IndividualWithFitness,
    IsSolutionValidArgs,
    PopulationWithFitness,
    SelectBestInvalidSolutionArgs,
    SelectParentsArgs,
    SelectWinnerSolutionArgs,
    SortPopulationByFitnessArgs,
)
from ..constants import TIME_LIMIT

from .calculation import calculate_route_duration


def sort_population_by_fitness(
    arg: SortPopulationByFitnessArgs,
) -> PopulationWithFitness:

    def sort_function(a, b):
        solution_a = a["individual"]
        solution_b = b["individual"]

        a_is_valid = is_solution_valid(
            IsSolutionValidArgs(
                duration_matrix=arg.duration_matrix, solution=solution_a
            )
        )
        b_is_valid = is_solution_valid(
            IsSolutionValidArgs(
                duration_matrix=arg.duration_matrix, solution=solution_b
            )
        )
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
            if b == select_best_invalid_solution(
                SelectBestInvalidSolutionArgs(
                    duration_matrix=arg.duration_matrix, solutions=[a, b]
                )
            ):
                return 1
            else:
                return -1

    return sorted(arg.population_fitness, key=cmp_to_key(sort_function))


def select_parents(arg: SelectParentsArgs) -> List[Individual]:

    parent1_contestants = random.choices(arg.population_fitness, k=2)
    parent2_contestants = random.choices(arg.population_fitness, k=2)

    parent1 = select_winner_solution(
        SelectWinnerSolutionArgs(
            duration_matrix=arg.duration_matrix, solutions=parent1_contestants
        )
    )
    parent2 = select_winner_solution(
        SelectWinnerSolutionArgs(
            duration_matrix=arg.duration_matrix, solutions=parent2_contestants
        )
    )

    return [parent1["individual"], parent2["individual"]]


def select_winner_solution(arg: SelectWinnerSolutionArgs) -> IndividualWithFitness:
    solution1 = arg.solutions[0]
    solution2 = arg.solutions[1]

    solution1_is_valid = is_solution_valid(
        IsSolutionValidArgs(
            duration_matrix=arg.duration_matrix, solution=solution1["individual"]
        )
    )
    solution2_is_valid = is_solution_valid(
        IsSolutionValidArgs(
            duration_matrix=arg.duration_matrix, solution=solution2["individual"]
        )
    )

    if solution1_is_valid and solution2_is_valid:
        return min(arg.solutions, key=lambda x: x["total_distance"])
    elif solution1_is_valid:
        return solution1
    elif solution2_is_valid:
        return solution2
    else:
        return select_best_invalid_solution(
            SelectBestInvalidSolutionArgs(
                duration_matrix=arg.duration_matrix, solutions=arg.solutions
            )
        )


def is_solution_valid(arg: IsSolutionValidArgs):
    all_cities = [city for vehicle in arg.solution for city in vehicle]
    is_there_any_priority_delivery = any(
        city.get("priority") == True for city in all_cities
    )

    if not is_there_any_priority_delivery:
        return True

    priority_checks: List[bool] = []

    for vehicle in arg.solution:
        priority_delivery_in_vehicle = any(
            city.get("priority") == True for city in vehicle
        )

        if not priority_delivery_in_vehicle:
            priority_checks.append(True)

        else:
            priority_cities_indices = [
                index
                for index, city in enumerate(vehicle)
                if city.get("priority") == True
            ]

            """
            Selects only the part of the route until last visited priority
            city and calculates the duration of this part of the route:
            """
            route_until_last_priority = vehicle[: (max(priority_cities_indices) + 1)]
            duration = calculate_route_duration(
                arg.duration_matrix, route_until_last_priority
            )
            # If duration exceeds time constraints, the solution isn't valid
            priority_checks.append(duration <= TIME_LIMIT)
    return len(priority_checks) > 0 and all(priority_checks)


def select_best_invalid_solution(
    arg: SelectBestInvalidSolutionArgs,
) -> dict[str, Individual | float | bool]:

    not_met_priorities: dict[int, List[int]] = {0: [], 1: []}
    total_delays: dict[int, float] = {0: 0, 1: 0}

    for index in range(len(arg.solutions)):
        solution_individual = arg.solutions[index]["individual"]

        for i in range(len(solution_individual)):
            vehicle = solution_individual[i]
            not_met_priorities[index].append(0)

            priority_delivery_in_vehicle = any(
                city.get("priority") == True for city in vehicle
            )

            if priority_delivery_in_vehicle:
                priority_cities_indices = [
                    p_index
                    for p_index, city in enumerate(vehicle)
                    if city.get("priority") == True
                ]
                for p_index in priority_cities_indices:
                    duration = calculate_route_duration(
                        arg.duration_matrix, vehicle[: p_index + 1]
                    )

                    if duration > TIME_LIMIT:
                        not_met_priorities[index][i] += 1
                        total_delays[index] += duration - TIME_LIMIT

    total_unmet_priorities_a = sum(count for count in not_met_priorities[0])

    total_unmet_priorities_b = sum(count for count in not_met_priorities[1])

    if total_unmet_priorities_a < total_unmet_priorities_b:
        return arg.solutions[0]
    elif total_unmet_priorities_a > total_unmet_priorities_b:
        return arg.solutions[1]
    elif total_delays[0] < total_delays[1]:
        return arg.solutions[0]
    elif total_delays[0] > total_delays[1]:
        return arg.solutions[1]
    else:
        return min(arg.solutions, key=lambda solution: solution["total_distance"])
