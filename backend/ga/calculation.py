from itertools import chain
from typing import List

from ..services import fetch_distances
from ..constants import TIME_LIMIT
from ..models import CityEntity, Individual, Matrix


# Calculate the HGV-driving distance and duration for all cities pairs.
def calculate_routes(
    cities: List[CityEntity],
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
    distances_matrix: Matrix,
    individual: Individual,
) -> float:

    individual_distance = 0

    for vehicle in individual:
        vehicle_distance = 0
        vehicle_length = len(vehicle)

        for i in range(vehicle_length - 1):
            vehicle_distance += get_distance(
                distances_matrix,
                vehicle[i]["id"],
                vehicle[i + 1]["id"],
            )
        individual_distance += vehicle_distance

    return individual_distance


def get_distance(
    distances_matrix: Matrix,
    location1: int,
    location2: int,
) -> float:

    return distances_matrix[(location1, location2)]


def are_priorities_on_time(
    durations_matrix: Matrix, solution: Individual, time_limit: int | None = TIME_LIMIT
) -> bool:
    all_cities = list(chain.from_iterable(solution))

    is_there_any_priority_delivery = any(
        city.get("priority") == True for city in all_cities
    )

    if not is_there_any_priority_delivery:
        return True

    priorities_check: List[bool] = []

    for vehicle in solution:
        priority_cities_indices = [
            index for index, city in enumerate(vehicle) if city.get("priority") == True
        ]

        if len(priority_cities_indices) == 0:
            priorities_check.append(True)
        else:
            higher_index = max(priority_cities_indices)
            critical_duration = calculate_route_duration(
                durations_matrix, vehicle[: higher_index + 1]
            )
            priorities_check.append(critical_duration <= time_limit)

    return len(priorities_check) > 0 and all(priorities_check)


def calculate_solution_duration(
    durations_matrix: Matrix,
    solution: Individual,
) -> float:
    all_routes_durations = []

    for vehicle in solution:
        vehicle_duration = 0

        for index in range(len(vehicle) - 1):
            current_city_id = vehicle[index]["id"]
            next_city_id = vehicle[index + 1]["id"]

            vehicle_duration += durations_matrix[(current_city_id, next_city_id)]

        all_routes_durations.append(vehicle_duration)

    return max(all_routes_durations)


def calculate_route_duration(
    durations_matrix: Matrix, vehicle: List[CityEntity]
) -> float:
    total_duration = 0

    for index in range(len(vehicle) - 1):
        current_city_id = vehicle[index]["id"]
        next_city_id = vehicle[index + 1]["id"]

        total_duration += durations_matrix[(current_city_id, next_city_id)]

    return total_duration
