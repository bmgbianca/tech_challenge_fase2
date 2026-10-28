from typing import List, Tuple

from ..services import fetch_distances
from ..config import CityEntity, Individual, Matrix


# Calculate the HGV-driving distance and duration for all cities pairs.
def calculate_routes(
    cities: List[dict[str, str | List[str] | Tuple[float, float]]],
) -> dict[str, Matrix]:

    cities_coordinates = [city["coordinates"] for city in cities]
    all_distances = fetch_distances(cities_coordinates)

    cities_distances = {}
    cities_durations = {}

    cities_size = len(cities)

    for firstIndex in range(cities_size):
        for secondIndex in range(cities_size):
            if firstIndex != secondIndex:
                cities_distances[
                    (
                        cities[firstIndex]["id"],
                        cities[secondIndex]["id"],
                    )
                ] = all_distances["distances"][firstIndex][secondIndex]

                cities_durations[
                    (
                        cities[firstIndex]["id"],
                        cities[secondIndex]["id"],
                    )
                ] = all_distances["durations"][firstIndex][secondIndex]
    return {"cities_distances": cities_distances, "cities_durations": cities_durations}


# Calculate the fitness of a given path based on the previous calculated distance.
def calculate_fitness(
    all_distances: Matrix,
    individual: List[CityEntity],
) -> float:

    distance = 0
    individual_length = len(individual)

    for i in range(individual_length - 1):
        distance += get_distance(
            all_distances,
            individual[i]["id"],
            individual[i + 1]["id"],
        )

    return distance


def get_distance(
    all_distances: Matrix,
    location1: Tuple[int, int],
    location2: Tuple[int, int],
) -> float:
    return all_distances.get((location1, location2), 0.0)


def calculate_critical_duration(durations_matrix: Matrix, solution: Individual):
    is_there_any_priority_delivery = any(
        city.get("priority") == True for city in solution
    )

    if not is_there_any_priority_delivery:
        return 0

    priority_cities_indices = [
        index for index, city in enumerate(solution) if city.get("priority") == True
    ]
    higher_index = max(priority_cities_indices)
    critical_duration = calculate_solution_duration(
        durations_matrix, solution[: higher_index + 1]
    )
    return critical_duration


def calculate_solution_duration(
    durations_matrix: Matrix,
    solution: List[CityEntity],
) -> float:
    total_duration = 0

    for index in range(len(solution) - 1):
        current_city_location = solution[index]["id"]
        next_city_location = solution[index + 1]["id"]

        current_route_duration = durations_matrix[
            current_city_location, next_city_location
        ]

        total_duration += current_route_duration

    return total_duration
