from typing import List, Tuple
import random

from ..config import CityEntity, Matrix


def generate_initial_population(
    type: str,
    distances_matrix: Matrix,
    population_size: int,
    cities: List[CityEntity],
    fixed_start_city_name: str = None,
) -> List[CityEntity]:

    if type == "random":
        return generate_random_population(
            population_size, cities, fixed_start_city_name
        )

    elif type == "nearest_neighbor":
        return generate_nearest_neighbor_population(
            distances_matrix, population_size, cities, fixed_start_city_name
        )

    elif type == "cheapest_insertion":
        return generate_cheapest_insertion_population(
            distances_matrix, population_size, cities, fixed_start_city_name
        )

    else:
        return generate_random_population(
            population_size, cities, fixed_start_city_name
        )


def generate_random_population(
    population_size: int, cities: List[CityEntity], fixed_start_city_name: str = None
) -> List[CityEntity]:

    initial_population = [
        random.sample(cities, len(cities)) for _ in range(population_size)
    ]

    if fixed_start_city_name is not None:
        start_city = next(
            (city for city in cities if city["name"] == fixed_start_city_name), None
        )
        if start_city is None:
            raise ValueError(
                f"City with name '{fixed_start_city_name}' not found in the cities list."
            )

        for individual in initial_population:
            individual.remove(start_city)
            individual.insert(0, start_city)

    return initial_population


def generate_start_city(
    cities: List[CityEntity], fixed_start_city_name: str = None
) -> CityEntity:
    fixed_start_city = None

    if fixed_start_city_name is not None:
        fixed_start_city = next(
            (city for city in cities if city["name"] == fixed_start_city_name), None
        )

        if fixed_start_city is None:
            raise ValueError(f"Cidade '{fixed_start_city_name}' não encontrada.")

    start_city = (
        fixed_start_city if fixed_start_city is not None else random.choice(cities)
    )

    return start_city


def generate_nearest_neighbor_individual(
    distances_matrix: dict[Tuple[Tuple[int, int], Tuple[int, int]], float],
    cities: List[CityEntity],
    start_city: CityEntity,
    possibilities_size: int = 4,
):

    unvisited_cities = [city for city in cities if city != start_city]
    new_individual = [start_city]
    current_city = start_city

    while len(unvisited_cities) > 0:
        current_location = current_city["id"]

        cities_sorted_by_distance = sorted(
            unvisited_cities,
            key=lambda city: distances_matrix[(current_location, city["id"])],
        )

        possible_next_cities = cities_sorted_by_distance[:possibilities_size]

        next_city = random.choice(possible_next_cities)
        new_individual.append(next_city)
        unvisited_cities.remove(next_city)
        current_city = next_city

    return new_individual


def generate_nearest_neighbor_population(
    distances_matrix: dict[Tuple[Tuple[int, int], Tuple[int, int]], float],
    population_size: int,
    cities: List[CityEntity],
    fixed_start_city_name: str = None,
) -> List[List[CityEntity]]:

    start_city = generate_start_city(cities, fixed_start_city_name)

    nearest_neighbor_population = []

    best_individual = generate_nearest_neighbor_individual(
        distances_matrix, cities, start_city, 1
    )
    nearest_neighbor_population.append(best_individual)

    max_attempts = 3
    current_attempt = 0

    while len(nearest_neighbor_population) < population_size:
        new_individual = generate_nearest_neighbor_individual(
            distances_matrix, cities, start_city, 4
        )

        if new_individual not in nearest_neighbor_population:
            nearest_neighbor_population.append(new_individual)
            current_attempt = 0
        else:
            current_attempt += 1

            if current_attempt >= max_attempts:
                nearest_neighbor_population.append(new_individual)
                current_attempt = 0

    return nearest_neighbor_population


def generate_cheapest_insertion_individual(
    distances_matrix: dict[Tuple[Tuple[int, int], Tuple[int, int]], float],
    cities: List[CityEntity],
    fixed_start_city_name: str = None,
):

    start_city = generate_start_city(cities, fixed_start_city_name)
    new_individual = [start_city]
    unvisited_cities = [city for city in cities if city != start_city]

    next_city = random.choice(unvisited_cities)
    total_distance = distances_matrix[
        (start_city["id"], next_city["id"])
    ]
    new_individual.append(next_city)
    unvisited_cities.remove(next_city)

    while len(unvisited_cities) > 0:
        new_individual_length = len(new_individual)
        possible_new_distances: List[Tuple[int, float]] = []

        city_to_insert = random.choice(unvisited_cities)
        location_to_insert = city_to_insert["id"]

        for index in range(1, new_individual_length):
            new_distance = total_distance

            new_individual_city_to_insertion_city = distances_matrix[
                (
                    new_individual[index - 1]["id"],
                    (location_to_insert),
                )
            ]

            insertion_city_to_new_individual_city = distances_matrix[
                (location_to_insert, new_individual[index]["id"])
            ]

            current_distance_to_be_replaced = distances_matrix[
                (
                    new_individual[index - 1]["id"],
                    new_individual[index]["id"],
                )
            ]

            new_distance = (
                total_distance
                + new_individual_city_to_insertion_city
                + insertion_city_to_new_individual_city
                - current_distance_to_be_replaced
            )

            possible_new_distances.append((index, new_distance))

        possible_new_distances.append(
            (
                new_individual_length,
                total_distance
                + distances_matrix[
                    (
                        new_individual[-1]["id"],
                        location_to_insert,
                    )
                ],
            )
        )

        cheapest_insertion = min(
            possible_new_distances,
            key=lambda index_distances: index_distances[1],
        )

        total_distance = cheapest_insertion[1]
        new_individual.insert(cheapest_insertion[0], city_to_insert)

        unvisited_cities.remove(city_to_insert)

    return new_individual


def generate_cheapest_insertion_population(
    distances_matrix: dict[Tuple[Tuple[int, int], Tuple[int, int]], float],
    population_size: int,
    cities: List[CityEntity],
    fixed_start_city_name: str = None,
) -> List[List[CityEntity]]:

    cheapest_insertion_population = []
    max_attempts = 3
    current_attempt = 0

    while len(cheapest_insertion_population) < population_size:
        new_individual = generate_cheapest_insertion_individual(
            distances_matrix, cities, fixed_start_city_name
        )

        if new_individual not in cheapest_insertion_population:
            cheapest_insertion_population.append(new_individual)
            current_attempt = 0
        else:
            current_attempt += 1

            if current_attempt >= max_attempts:
                cheapest_insertion_population.append(new_individual)
                current_attempt = 0

    return cheapest_insertion_population
