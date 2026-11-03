import copy
import math
from typing import List, Tuple
import random

from ...models import (
    CityEntity,
    GenerateCIIndividualArgs,
    GenerateNNIndividualArgs,
    GetBestNNCityArgs,
    Individual,
)


def get_complete_origin_city(
    cities: List[CityEntity], origin_city_name: str | None = None
):
    complete_origin_city = next(
        (city for city in cities if city["name"] == origin_city_name), None
    )

    if complete_origin_city is None:
        raise ValueError(f"Cidade {origin_city_name} não encontrada.")

    return complete_origin_city


"""If origin_city_name, removes it (-1) from cities_length because 
origin_city must be placed in every vehicle route:
"""


def get_cities_distribution(
    cities: List[CityEntity],
    is_origin: bool,
    vehicles_number: int | None = 1,
) -> Tuple[int, int]:
    cities_length = len(cities) - 1 if is_origin else len(cities)

    if vehicles_number < 1:
        raise ValueError("O número de veículos deve ser de pelo menos 1.")

    if vehicles_number > cities_length:
        raise ValueError(
            f"O número de veículos ({vehicles_number}) não pode ser maior "
            f"que o número de cidades a visitar ({cities_length})."
        )

    cities_per_vehicle = math.floor(cities_length / vehicles_number)
    remaining_cities_amount = cities_length % vehicles_number

    return cities_per_vehicle, remaining_cities_amount


"""possibilities_size argument is needed in order to generate various 
different individuals"""


def generate_start_city(
    cities: List[CityEntity], origin_city: str = None
) -> CityEntity:
    origin = None

    if origin_city is not None:
        origin = next((city for city in cities if city["name"] == origin_city), None)

        if origin is None:
            raise ValueError(f"Cidade '{origin_city}' não encontrada.")

    start_city = origin if origin is not None else random.choice(cities)

    return start_city


def get_best_nn_next_city(arg: GetBestNNCityArgs) -> CityEntity:
    current_id = arg.current_city["id"]

    cities_sorted_by_distance = sorted(
        arg.cities, key=lambda city: arg.distances_matrix[(current_id, city["id"])]
    )

    possible_next_cities = cities_sorted_by_distance[: arg.possibilities_size]

    next_city = random.choice(possible_next_cities)
    return next_city


def generate_new_nn_individual(arg: GenerateNNIndividualArgs) -> Individual:
    current_individual = []
    cities_per_vehicle = (
        arg.cities_per_vehicle + 1 if arg.origin else arg.cities_per_vehicle
    )
    unvisited_cities = (
        copy.deepcopy(arg.cities)
        if arg.origin is None
        else [city for city in arg.cities if city["name"] != arg.origin["name"]]
    )

    while len(current_individual) < arg.vehicles_number:
        start_city = arg.origin if bool(arg.origin) else random.choice(unvisited_cities)
        current_vehicle = [start_city]
        unvisited_cities = [
            city for city in unvisited_cities if city["name"] != start_city["name"]
        ]
        current_city = start_city

        while len(current_vehicle) < cities_per_vehicle:
            next_city = get_best_nn_next_city(
                GetBestNNCityArgs(
                    distances_matrix=arg.distances_matrix,
                    cities=unvisited_cities,
                    current_city=current_city,
                    possibilities_size=arg.possibilities_size,
                )
            )
            current_vehicle.append(next_city)
            unvisited_cities.remove(next_city)
            current_city = next_city

        current_individual.append(current_vehicle)

    """Cities left over by the even distribution go to the vehicle whose
    last city is the closest to them:"""
    if arg.remaining_cities_amount > 0:
        for city in unvisited_cities:
            closest_vehicle = min(
                current_individual,
                key=lambda vehicle: arg.distances_matrix[
                    (vehicle[-1]["id"], city["id"])
                ],
            )
            closest_vehicle.append(city)

    return current_individual


def generate_new_ci_individual(arg: GenerateCIIndividualArgs) -> Individual:
    distances = arg.distances_matrix
    cities_per_vehicle = (
        arg.cities_per_vehicle + 1 if arg.origin else arg.cities_per_vehicle
    )

    new_individual = []
    unvisited_cities = (
        copy.deepcopy(arg.cities)
        if arg.origin is None
        else [city for city in arg.cities if city["name"] != arg.origin["name"]]
    )

    while len(new_individual) < arg.vehicles_number:
        start_city = arg.origin if arg.origin else random.choice(unvisited_cities)
        unvisited_cities = [
            city for city in unvisited_cities if city["name"] != start_city["name"]
        ]
        current_vehicle = [start_city]
        second_city = random.choice(unvisited_cities)
        current_vehicle.append(second_city)
        unvisited_cities.remove(second_city)

        total_distance = distances[start_city["id"], second_city["id"]]

        while len(current_vehicle) < cities_per_vehicle:
            possible_new_distances: List[Tuple[int, float]] = []

            current_vehicle_length = len(current_vehicle)
            city_to_insert = random.choice(unvisited_cities)
            id_to_insert = city_to_insert["id"]

            current_last_city_id = current_vehicle[-1]["id"]
            new_distance = (
                total_distance + distances[current_last_city_id, id_to_insert]
            )

            possible_new_distances.append((current_vehicle_length, new_distance))

            for index in range(1, current_vehicle_length):
                previous_city = current_vehicle[index - 1]
                next_city = current_vehicle[index]

                previous_city_to_current_city_distance = distances[
                    previous_city["id"], id_to_insert
                ]
                current_city_to_next_city_distance = distances[
                    id_to_insert, next_city["id"]
                ]
                previous_city_to_next_city_distance = distances[
                    previous_city["id"], next_city["id"]
                ]

                current_new_distance = (
                    total_distance
                    + previous_city_to_current_city_distance
                    + current_city_to_next_city_distance
                    - previous_city_to_next_city_distance
                )

                possible_new_distances.append((index, current_new_distance))

            cheapest_insertion = min(
                possible_new_distances,
                key=lambda index_distance: index_distance[1],
            )

            total_distance = cheapest_insertion[1]
            current_vehicle.insert(cheapest_insertion[0], city_to_insert)

            unvisited_cities.remove(city_to_insert)

        new_individual.append(current_vehicle)

    """Cities left over by the even distribution are inserted in the vehicle
    and in the position where the total distance increases the least:"""
    if arg.remaining_cities_amount > 0:
        while len(unvisited_cities) > 0:
            city_to_insert = random.choice(unvisited_cities)
            id_to_insert = city_to_insert["id"]

            possible_insertions: List[Tuple[float, int, int]] = []

            for vehicle_index, vehicle in enumerate(new_individual):
                vehicle_length = len(vehicle)

                last_city_to_insertion_city_distance = distances[
                    vehicle[-1]["id"], id_to_insert
                ]
                possible_insertions.append(
                    (
                        last_city_to_insertion_city_distance,
                        vehicle_index,
                        vehicle_length,
                    )
                )

                for index in range(1, vehicle_length):
                    previous_city = vehicle[index - 1]
                    next_city = vehicle[index]

                    distance_increase = (
                        distances[previous_city["id"], id_to_insert]
                        + distances[id_to_insert, next_city["id"]]
                        - distances[previous_city["id"], next_city["id"]]
                    )

                    possible_insertions.append(
                        (distance_increase, vehicle_index, index)
                    )

            _, best_vehicle_index, best_position = min(
                possible_insertions,
                key=lambda insertion: insertion[0],
            )

            new_individual[best_vehicle_index].insert(best_position, city_to_insert)
            unvisited_cities.remove(city_to_insert)

    return new_individual
