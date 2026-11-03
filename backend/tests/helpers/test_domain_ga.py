from unittest.mock import patch

import pytest

from backend.helpers.domain import (
    GenerateCIIndividualArgs,
    GenerateNNIndividualArgs,
    GetBestNNCityArgs,
    generate_new_ci_individual,
    generate_new_nn_individual,
    get_best_nn_next_city,
    get_cities_distribution,
    get_complete_origin_city,
)


def make_city(name, city_id):
    return {"name": name, "id": city_id, "priority": False}


@pytest.fixture
def cities():
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


def route_names(individual):
    return [[city["name"] for city in route] for route in individual]


class TestGetCompleteOriginCity:
    def test_returns_the_city_with_the_given_name(self, cities):
        assert get_complete_origin_city(cities, "C") is cities[2]

    def test_raises_when_city_not_found(self, cities):
        with pytest.raises(ValueError):
            get_complete_origin_city(cities, "Nonexistent")


class TestGetCitiesDistribution:
    @pytest.mark.parametrize(
        "cities_amount, vehicles_number, is_origin, expected",
        [
            (7, 2, True, (3, 0)),
            (7, 3, True, (2, 0)),
            (8, 3, True, (2, 1)),
            (7, 2, False, (3, 1)),
            (7, 1, False, (7, 0)),
            (4, 3, True, (1, 0)),
        ],
    )
    def test_splits_cities_between_vehicles(
        self, cities_amount, vehicles_number, is_origin, expected
    ):
        cities = [make_city(str(index), index) for index in range(cities_amount)]
        assert get_cities_distribution(cities, is_origin, vehicles_number) == expected

    @pytest.mark.parametrize(
        "cities_amount, vehicles_number, is_origin",
        [
            (4, 4, True),  # 3 clients (origin excluded) for 4 vehicles
            (7, 7, True),
            (3, 4, False),
            (4, 0, True),
            (4, -1, False),
        ],
    )
    def test_raises_when_vehicles_number_is_invalid(
        self, cities_amount, vehicles_number, is_origin
    ):
        cities = [make_city(str(index), index) for index in range(cities_amount)]
        with pytest.raises(ValueError):
            get_cities_distribution(cities, is_origin, vehicles_number)

    def test_accepts_as_many_vehicles_as_cities_to_visit(self):
        cities = [make_city(str(index), index) for index in range(4)]
        assert get_cities_distribution(cities, True, 3) == (1, 0)
        assert get_cities_distribution(cities, False, 4) == (1, 0)


class TestGetBestNNNextCity:
    def test_possibilities_size_defaults_to_four(self, cities, distances_matrix):
        args = GetBestNNCityArgs(
            distances_matrix=distances_matrix,
            cities=cities[1:],
            current_city=cities[0],
        )
        assert args.possibilities_size == 4

    def test_returns_the_nearest_city_when_possibilities_size_is_one(
        self, cities, distances_matrix
    ):
        next_city = get_best_nn_next_city(
            GetBestNNCityArgs(
                distances_matrix=distances_matrix,
                cities=[cities[3], cities[1], cities[5]],
                current_city=cities[0],
                possibilities_size=1,
            )
        )
        assert next_city is cities[1]

    def test_picks_among_the_nearest_cities_only(self, cities, distances_matrix):
        candidates = [cities[3], cities[1], cities[5], cities[6]]
        nearest_two = {"B", "D"}

        for _ in range(50):
            next_city = get_best_nn_next_city(
                GetBestNNCityArgs(
                    distances_matrix=distances_matrix,
                    cities=candidates,
                    current_city=cities[0],
                    possibilities_size=2,
                )
            )
            assert next_city["name"] in nearest_two


class TestGenerateNewNNIndividual:
    def make_args(self, cities, distances_matrix, **overrides):
        args = {
            "distances_matrix": distances_matrix,
            "cities": cities,
            "cities_per_vehicle": 3,
            "remaining_cities_amount": 0,
            "vehicles_number": 2,
            "origin": cities[0],
            "possibilities_size": 1,
        }
        args.update(overrides)
        return GenerateNNIndividualArgs(**args)

    def test_greedy_individual_with_origin(self, cities, distances_matrix):
        individual = generate_new_nn_individual(
            self.make_args(cities, distances_matrix)
        )
        assert route_names(individual) == [["A", "B", "C", "D"], ["A", "E", "F", "G"]]

    def test_remaining_cities_go_to_the_vehicle_with_the_closest_last_city(
        self, cities, distances_matrix
    ):
        # 6 clients, 4 vehicles: 1 client each (B, C, D, E) + 2 remaining (F, G).
        # F is closest to E (last city of the 4th vehicle), and then G is
        # closest to F, which is now the last city of that same vehicle
        individual = generate_new_nn_individual(
            self.make_args(
                cities,
                distances_matrix,
                cities_per_vehicle=1,
                remaining_cities_amount=2,
                vehicles_number=4,
            )
        )
        assert route_names(individual) == [
            ["A", "B"],
            ["A", "C"],
            ["A", "D"],
            ["A", "E", "F", "G"],
        ]

    def test_without_origin_every_city_is_visited_once(self, cities, distances_matrix):
        individual = generate_new_nn_individual(
            self.make_args(
                cities,
                distances_matrix,
                cities_per_vehicle=3,
                remaining_cities_amount=1,
                origin=None,
            )
        )
        visited_ids = [city["id"] for route in individual for city in route]
        assert sorted(visited_ids) == list(range(7))

    def test_does_not_change_the_given_cities_list(self, cities, distances_matrix):
        names_before = [city["name"] for city in cities]
        generate_new_nn_individual(self.make_args(cities, distances_matrix))
        assert [city["name"] for city in cities] == names_before


class TestGenerateNewCIIndividual:
    def make_args(self, cities, distances_matrix, **overrides):
        args = {
            "distances_matrix": distances_matrix,
            "cities": cities,
            "cities_per_vehicle": 3,
            "remaining_cities_amount": 0,
            "origin": cities[0],
            "vehicles_number": 2,
        }
        args.update(overrides)
        return GenerateCIIndividualArgs(**args)

    @staticmethod
    def total_distance(individual, distances_matrix):
        return sum(
            distances_matrix[(route[index]["id"], route[index + 1]["id"])]
            for route in individual
            for index in range(len(route) - 1)
        )

    def test_origin_starts_every_route_and_clients_are_visited_once(
        self, cities, distances_matrix
    ):
        for _ in range(20):
            individual = generate_new_ci_individual(
                self.make_args(cities, distances_matrix)
            )
            assert len(individual) == 2
            assert all(route[0] is cities[0] for route in individual)

            visited_ids = [city["id"] for route in individual for city in route[1:]]
            assert sorted(visited_ids) == [1, 2, 3, 4, 5, 6]

    def test_remaining_cities_are_all_inserted(self, cities, distances_matrix):
        # 6 clients, 4 vehicles: 1 client each + 2 remaining
        for _ in range(20):
            individual = generate_new_ci_individual(
                self.make_args(
                    cities,
                    distances_matrix,
                    cities_per_vehicle=1,
                    remaining_cities_amount=2,
                    vehicles_number=4,
                )
            )
            visited_ids = [city["id"] for route in individual for city in route[1:]]
            assert sorted(visited_ids) == [1, 2, 3, 4, 5, 6]

    def test_without_origin_every_city_is_visited_once(self, cities, distances_matrix):
        for _ in range(20):
            individual = generate_new_ci_individual(
                self.make_args(
                    cities,
                    distances_matrix,
                    cities_per_vehicle=3,
                    remaining_cities_amount=1,
                    origin=None,
                )
            )
            visited_ids = [city["id"] for route in individual for city in route]
            assert sorted(visited_ids) == list(range(7))

    def test_remaining_city_goes_to_the_vehicle_end_that_costs_the_least(
        self, cities, distances_matrix
    ):
        # always picking the first candidate makes the individual deterministic:
        # [A, B, C] and [A, D, E] are built first, then F and G are left over.
        # F is cheapest at the end of the second vehicle (+1), and so is G (+1)
        with patch(
            "backend.helpers.domain.ga.random.choice", side_effect=lambda seq: seq[0]
        ):
            individual = generate_new_ci_individual(
                self.make_args(
                    cities,
                    distances_matrix,
                    cities_per_vehicle=2,
                    remaining_cities_amount=2,
                )
            )
        assert route_names(individual) == [["A", "B", "C"], ["A", "D", "E", "F", "G"]]

    def test_remaining_cities_are_inserted_in_the_middle_when_it_costs_nothing(
        self, cities, distances_matrix
    ):
        # always picking the last candidate builds [A, F, G] (distance 6) and
        # [A, D, E] (distance 4), leaving B and C over. Both lie between A and
        # the next city of a route, so they can be inserted without increasing
        # the total distance
        with patch(
            "backend.helpers.domain.ga.random.choice", side_effect=lambda seq: seq[-1]
        ):
            individual = generate_new_ci_individual(
                self.make_args(
                    cities,
                    distances_matrix,
                    cities_per_vehicle=2,
                    remaining_cities_amount=2,
                )
            )

        assert self.total_distance(individual, distances_matrix) == 10

        visited_ids = [city["id"] for route in individual for city in route[1:]]
        assert sorted(visited_ids) == [1, 2, 3, 4, 5, 6]

    def test_does_not_change_the_given_cities_list(self, cities, distances_matrix):
        names_before = [city["name"] for city in cities]
        generate_new_ci_individual(self.make_args(cities, distances_matrix))
        assert [city["name"] for city in cities] == names_before
