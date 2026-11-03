import copy
from typing import List
import random

from ..models import (
    GenerateCheapestInsertionArgs,
    GenerateNearestNeighborArgs,
    GenerateRandomArgs,
    Individual,
    InitialPopulationArgs,
)
from ..helpers.domain import (
    GenerateCIIndividualArgs,
    GenerateNNIndividualArgs,
    generate_new_nn_individual,
    generate_new_ci_individual,
    get_cities_distribution,
    get_complete_origin_city,
)


def generate_initial_population(arg: InitialPopulationArgs) -> List[Individual]:
    cities_names = [city["name"] for city in arg.cities]

    if bool(arg.origin_city_name) and arg.origin_city_name not in cities_names:
        raise ValueError(f"Cidade {arg.origin_city_name} não encontrada")

    if arg.population_strategy == "nearest_neighbor":
        return generate_nearest_neighbor_population(
            GenerateNearestNeighborArgs(
                distances_matrix=arg.distances_matrix,
                population_size=arg.population_size,
                cities=arg.cities,
                origin_city_name=arg.origin_city_name,
                vehicles_number=arg.vehicles_number,
            )
        )

    elif arg.population_strategy == "cheapest_insertion":
        return generate_cheapest_insertion_population(
            GenerateCheapestInsertionArgs(
                distances_matrix=arg.distances_matrix,
                population_size=arg.population_size,
                cities=arg.cities,
                origin_city_name=arg.origin_city_name,
                vehicles_number=arg.vehicles_number,
            )
        )

    else:
        return generate_random_population(
            GenerateRandomArgs(
                population_size=arg.population_size,
                cities=arg.cities,
                origin_city_name=arg.origin_city_name,
                vehicles_number=arg.vehicles_number,
            )
        )


def generate_random_population(arg: GenerateRandomArgs) -> List[Individual]:
    population_size = arg.population_size
    cities = arg.cities
    origin_city_name = arg.origin_city_name
    vehicles_number = arg.vehicles_number
    initial_population: List[Individual] = []

    cities_per_vehicle, remaining_cities_amount = get_cities_distribution(
        cities,
        bool(origin_city_name),
        vehicles_number,
    )

    if origin_city_name:
        origin = get_complete_origin_city(cities, origin_city_name)

        while len(initial_population) < population_size:
            current_individual = []
            unvisited_cities = [
                city for city in cities if city["name"] != origin_city_name
            ]

            for _ in range(vehicles_number):
                current_vehicle = [origin] + random.sample(
                    unvisited_cities, cities_per_vehicle
                )
                current_individual.append(current_vehicle)
                unvisited_cities = [
                    city for city in unvisited_cities if city not in current_vehicle
                ]

            if remaining_cities_amount != 0:
                for index in range(len(unvisited_cities)):
                    current_individual[index].append(unvisited_cities[index])

            initial_population.append(current_individual)

    else:
        for _ in range(population_size):
            current_individual = []
            unvisited_cities = copy.deepcopy(cities)

            for _ in range(vehicles_number):
                current_vehicle = random.sample(unvisited_cities, cities_per_vehicle)
                current_individual.append(current_vehicle)
                unvisited_cities = [
                    city for city in unvisited_cities if city not in current_vehicle
                ]

            if remaining_cities_amount != 0:
                for index in range(len(unvisited_cities)):
                    current_individual[index].append(unvisited_cities[index])

            initial_population.append(current_individual)

    return initial_population


def generate_nearest_neighbor_population(
    arg: GenerateNearestNeighborArgs,
) -> List[Individual]:
    cities_per_vehicle, remaining_cities_amount = get_cities_distribution(
        arg.cities,
        bool(arg.origin_city_name),
        arg.vehicles_number,
    )

    origin = (
        None
        if not arg.origin_city_name
        else get_complete_origin_city(arg.cities, arg.origin_city_name)
    )

    nearest_neighbor_population = []

    best_individual = generate_new_nn_individual(
        GenerateNNIndividualArgs(
            distances_matrix=arg.distances_matrix,
            cities=arg.cities,
            cities_per_vehicle=cities_per_vehicle,
            remaining_cities_amount=remaining_cities_amount,
            vehicles_number=arg.vehicles_number,
            origin=origin,
            possibilities_size=1,
        )
    )
    nearest_neighbor_population.append(best_individual)

    max_attempts = 3
    current_attempt = 0

    while len(nearest_neighbor_population) < arg.population_size:
        new_individual = generate_new_nn_individual(
            GenerateNNIndividualArgs(
                distances_matrix=arg.distances_matrix,
                cities=arg.cities,
                cities_per_vehicle=cities_per_vehicle,
                remaining_cities_amount=remaining_cities_amount,
                vehicles_number=arg.vehicles_number,
                origin=origin,
                possibilities_size=4,
            )
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


def generate_cheapest_insertion_population(
    arg: GenerateCheapestInsertionArgs,
) -> List[Individual]:
    origin = (
        None
        if not arg.origin_city_name
        else get_complete_origin_city(arg.cities, arg.origin_city_name)
    )

    cities_per_vehicle, remaining_cities_amount = get_cities_distribution(
        arg.cities,
        bool(arg.origin_city_name),
        arg.vehicles_number,
    )

    max_attempts = 3
    current_attempt = 0

    cheapest_insertion_population = []
    while len(cheapest_insertion_population) < arg.population_size:
        new_individual = generate_new_ci_individual(
            GenerateCIIndividualArgs(
                distances_matrix=arg.distances_matrix,
                cities=arg.cities,
                cities_per_vehicle=cities_per_vehicle,
                remaining_cities_amount=remaining_cities_amount,
                origin=origin,
                vehicles_number=arg.vehicles_number,
            )
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
