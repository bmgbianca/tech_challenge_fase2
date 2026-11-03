from unittest.mock import patch

import pytest

from backend.ga.initial_population import (
    GenerateCheapestInsertionArgs,
    GenerateNearestNeighborArgs,
    GenerateRandomArgs,
    InitialPopulationArgs,
    generate_cheapest_insertion_population,
    generate_initial_population,
    generate_nearest_neighbor_population,
    generate_random_population,
)

from backend.helpers import generate_start_city

ORIGIN_NAME = "A"


def make_city(name, city_id):
    return {"name": name, "id": city_id, "priority": False}


@pytest.fixture
def cities():
    # 7 cities, origin "A" has id 0, so there are 6 clients to distribute
    return [make_city(name, index) for index, name in enumerate("ABCDEFG")]


@pytest.fixture
def distances_matrix(cities):
    # cities lie on a line: distance is the difference between ids
    return {
        (city_a["id"], city_b["id"]): abs(city_a["id"] - city_b["id"])
        for city_a in cities
        for city_b in cities
        if city_a is not city_b
    }


def assert_valid_individual(individual, cities, vehicles_number, has_origin=True):
    """Every city must be visited exactly once (the origin is the exception:
    it starts every vehicle route)."""
    assert len(individual) == vehicles_number

    if has_origin:
        assert all(route[0]["name"] == ORIGIN_NAME for route in individual)
        visited_ids = [city["id"] for route in individual for city in route[1:]]
        expected_ids = [city["id"] for city in cities if city["name"] != ORIGIN_NAME]
    else:
        visited_ids = [city["id"] for route in individual for city in route]
        expected_ids = [city["id"] for city in cities]

    assert sorted(visited_ids) == sorted(expected_ids)


def route_names(individual):
    return [[city["name"] for city in route] for route in individual]


class TestGenerateRandomPopulation:
    def test_population_has_requested_size(self, cities):
        population = generate_random_population(
            GenerateRandomArgs(
                population_size=5, cities=cities, origin_city_name=ORIGIN_NAME
            )
        )
        assert len(population) == 5

    @pytest.mark.parametrize("vehicles_number", [1, 2, 3, 4])
    def test_origin_starts_every_route_and_clients_are_visited_once(
        self, cities, vehicles_number
    ):
        population = generate_random_population(
            GenerateRandomArgs(
                population_size=10,
                cities=cities,
                origin_city_name=ORIGIN_NAME,
                vehicles_number=vehicles_number,
            )
        )
        for individual in population:
            assert_valid_individual(individual, cities, vehicles_number)

    @pytest.mark.parametrize("vehicles_number", [1, 2, 3])
    def test_works_without_origin(self, cities, vehicles_number):
        population = generate_random_population(
            GenerateRandomArgs(
                population_size=10,
                cities=cities,
                vehicles_number=vehicles_number,
            )
        )
        for individual in population:
            assert_valid_individual(
                individual, cities, vehicles_number, has_origin=False
            )

    def test_routes_are_balanced_between_vehicles(self, cities):
        # 6 clients and 3 vehicles: 2 clients per vehicle (+ origin)
        population = generate_random_population(
            GenerateRandomArgs(
                population_size=10,
                cities=cities,
                origin_city_name=ORIGIN_NAME,
                vehicles_number=3,
            )
        )
        for individual in population:
            assert [len(route) for route in individual] == [3, 3, 3]

    def test_remaining_cities_go_to_the_first_vehicles(self, cities):
        # 6 clients and 4 vehicles: 1 client each, the 2 remaining go to the
        # first two vehicles
        population = generate_random_population(
            GenerateRandomArgs(
                population_size=10,
                cities=cities,
                origin_city_name=ORIGIN_NAME,
                vehicles_number=4,
            )
        )
        for individual in population:
            assert [len(route) for route in individual] == [3, 3, 2, 2]

    def test_raises_when_origin_not_found(self, cities):
        with pytest.raises(ValueError):
            generate_random_population(
                GenerateRandomArgs(
                    population_size=5, cities=cities, origin_city_name="Nonexistent"
                )
            )


class TestGenerateNearestNeighborPopulation:
    def test_population_has_requested_size(self, cities, distances_matrix):
        population = generate_nearest_neighbor_population(
            GenerateNearestNeighborArgs(
                distances_matrix=distances_matrix,
                population_size=5,
                cities=cities,
                origin_city_name=ORIGIN_NAME,
            )
        )
        assert len(population) == 5

    @pytest.mark.parametrize("vehicles_number", [1, 2, 3, 4])
    def test_origin_starts_every_route_and_clients_are_visited_once(
        self, cities, distances_matrix, vehicles_number
    ):
        population = generate_nearest_neighbor_population(
            GenerateNearestNeighborArgs(
                distances_matrix=distances_matrix,
                population_size=10,
                cities=cities,
                origin_city_name=ORIGIN_NAME,
                vehicles_number=vehicles_number,
            )
        )
        for individual in population:
            assert_valid_individual(individual, cities, vehicles_number)

    @pytest.mark.parametrize("vehicles_number", [1, 2, 3])
    def test_works_without_origin(self, cities, distances_matrix, vehicles_number):
        population = generate_nearest_neighbor_population(
            GenerateNearestNeighborArgs(
                distances_matrix=distances_matrix,
                population_size=10,
                cities=cities,
                vehicles_number=vehicles_number,
            )
        )
        for individual in population:
            assert_valid_individual(
                individual, cities, vehicles_number, has_origin=False
            )

    def test_first_individual_is_the_greedy_one_with_single_vehicle(
        self, cities, distances_matrix
    ):
        population = generate_nearest_neighbor_population(
            GenerateNearestNeighborArgs(
                distances_matrix=distances_matrix,
                population_size=5,
                cities=cities,
                origin_city_name=ORIGIN_NAME,
                vehicles_number=1,
            )
        )
        assert route_names(population[0]) == [["A", "B", "C", "D", "E", "F", "G"]]

    def test_first_individual_is_the_greedy_one_with_two_vehicles(
        self, cities, distances_matrix
    ):
        population = generate_nearest_neighbor_population(
            GenerateNearestNeighborArgs(
                distances_matrix=distances_matrix,
                population_size=5,
                cities=cities,
                origin_city_name=ORIGIN_NAME,
                vehicles_number=2,
            )
        )
        assert route_names(population[0]) == [
            ["A", "B", "C", "D"],
            ["A", "E", "F", "G"],
        ]

    def test_raises_when_origin_not_found(self, cities, distances_matrix):
        with pytest.raises(ValueError):
            generate_nearest_neighbor_population(
                GenerateNearestNeighborArgs(
                    distances_matrix=distances_matrix,
                    population_size=5,
                    cities=cities,
                    origin_city_name="Nonexistent",
                )
            )


class TestGenerateCheapestInsertionPopulation:
    def test_population_has_requested_size(self, cities, distances_matrix):
        population = generate_cheapest_insertion_population(
            GenerateCheapestInsertionArgs(
                distances_matrix=distances_matrix,
                population_size=5,
                cities=cities,
                origin_city_name=ORIGIN_NAME,
            )
        )
        assert len(population) == 5

    @pytest.mark.parametrize("vehicles_number", [1, 2, 3, 4])
    def test_origin_starts_every_route_and_clients_are_visited_once(
        self, cities, distances_matrix, vehicles_number
    ):
        population = generate_cheapest_insertion_population(
            GenerateCheapestInsertionArgs(
                distances_matrix=distances_matrix,
                population_size=10,
                cities=cities,
                origin_city_name=ORIGIN_NAME,
                vehicles_number=vehicles_number,
            )
        )
        for individual in population:
            assert_valid_individual(individual, cities, vehicles_number)

    @pytest.mark.parametrize("vehicles_number", [1, 2, 3])
    def test_works_without_origin(self, cities, distances_matrix, vehicles_number):
        population = generate_cheapest_insertion_population(
            GenerateCheapestInsertionArgs(
                distances_matrix=distances_matrix,
                population_size=10,
                cities=cities,
                vehicles_number=vehicles_number,
            )
        )
        for individual in population:
            assert_valid_individual(
                individual, cities, vehicles_number, has_origin=False
            )

    def test_single_vehicle_route_on_a_line_is_always_in_order(
        self, cities, distances_matrix
    ):
        # cities lie on a line and the origin is at one end: the cheapest
        # insertion always ends up with the cities sorted by distance
        population = generate_cheapest_insertion_population(
            GenerateCheapestInsertionArgs(
                distances_matrix=distances_matrix,
                population_size=5,
                cities=cities,
                origin_city_name=ORIGIN_NAME,
                vehicles_number=1,
            )
        )
        for individual in population:
            assert route_names(individual) == [["A", "B", "C", "D", "E", "F", "G"]]

    def test_raises_when_origin_not_found(self, cities, distances_matrix):
        with pytest.raises(ValueError):
            generate_cheapest_insertion_population(
                GenerateCheapestInsertionArgs(
                    distances_matrix=distances_matrix,
                    population_size=5,
                    cities=cities,
                    origin_city_name="Nonexistent",
                )
            )


class TestGenerateInitialPopulation:
    def make_args(self, cities, distances_matrix, **overrides):
        args = {
            "population_strategy": "random",
            "distances_matrix": distances_matrix,
            "population_size": 5,
            "cities": cities,
            "origin_city_name": ORIGIN_NAME,
        }
        args.update(overrides)
        return InitialPopulationArgs(**args)

    @pytest.mark.parametrize(
        "strategy", ["random", "nearest_neighbor", "cheapest_insertion"]
    )
    def test_generates_valid_population_for_each_strategy(
        self, cities, distances_matrix, strategy
    ):
        population = generate_initial_population(
            self.make_args(
                cities,
                distances_matrix,
                population_strategy=strategy,
                vehicles_number=2,
            )
        )
        assert len(population) == 5
        for individual in population:
            assert_valid_individual(individual, cities, 2)

    def test_unknown_strategy_falls_back_to_random(self, cities, distances_matrix):
        population = generate_initial_population(
            self.make_args(cities, distances_matrix, population_strategy="unknown")
        )
        assert len(population) == 5
        for individual in population:
            assert_valid_individual(individual, cities, 1)

    @pytest.mark.parametrize(
        "strategy", ["random", "nearest_neighbor", "cheapest_insertion", "unknown"]
    )
    def test_raises_when_there_are_more_vehicles_than_cities_to_visit(
        self, cities, distances_matrix, strategy
    ):
        # 7 cities with the origin leaves 6 cities to visit
        with pytest.raises(ValueError):
            generate_initial_population(
                self.make_args(
                    cities,
                    distances_matrix,
                    population_strategy=strategy,
                    vehicles_number=len(cities),
                )
            )

    def test_vehicles_number_defaults_to_one(self, cities, distances_matrix):
        population = generate_initial_population(
            self.make_args(cities, distances_matrix)
        )
        assert all(len(individual) == 1 for individual in population)

    def test_raises_when_origin_not_found(self, cities, distances_matrix):
        with pytest.raises(ValueError):
            generate_initial_population(
                self.make_args(cities, distances_matrix, origin_city_name="Nonexistent")
            )

    @pytest.mark.parametrize(
        "strategy, function_name",
        [
            ("random", "generate_random_population"),
            ("nearest_neighbor", "generate_nearest_neighbor_population"),
            ("cheapest_insertion", "generate_cheapest_insertion_population"),
        ],
    )
    def test_dispatches_to_the_matching_generator(
        self, cities, distances_matrix, strategy, function_name
    ):
        with patch(f"backend.ga.initial_population.{function_name}") as generator:
            generate_initial_population(
                self.make_args(cities, distances_matrix, population_strategy=strategy)
            )
        generator.assert_called_once()


class TestGenerateStartCity:
    def test_returns_requested_city(self, cities):
        start_city = generate_start_city(cities, origin_city="B")
        assert start_city["name"] == "B"

    def test_raises_when_city_not_found(self, cities):
        with pytest.raises(ValueError):
            generate_start_city(cities, origin_city="Nonexistent")

    def test_returns_a_city_from_the_list_when_no_origin(self, cities):
        start_city = generate_start_city(cities)
        assert start_city in cities
