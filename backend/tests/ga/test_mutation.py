import copy
from unittest.mock import patch

import pytest

from backend.ga import segment_shuffle_mutation


def make_city(name, city_id):
    return {"name": name, "id": city_id, "priority": False}


def mutate(individual, mutation_probability=1.0, is_origin=True):
    return segment_shuffle_mutation(
        {
            "individual": individual,
            "mutation_probability": mutation_probability,
            "is_origin": is_origin,
        }
    )


def route_names(individual):
    return [[city["name"] for city in route] for route in individual]


def count_changed_routes(before, after):
    return sum(
        route_before != route_after for route_before, route_after in zip(before, after)
    )


@pytest.fixture
def cities():
    return {name: make_city(name, index) for index, name in enumerate("ABCDEFGHIJ")}


def build(cities, *routes):
    return [[cities[name] for name in route] for route in routes]


# (routes, is_origin): every route starts with the origin "A" when is_origin
INDIVIDUALS = [
    pytest.param(["ABCD", "AEFG"], True, id="origin-2-vehicles"),
    pytest.param(["ABCDEFGHIJ"], True, id="origin-1-vehicle-long-route"),
    pytest.param(["AB", "AC", "ADEFG"], True, id="origin-short-routes"),
    pytest.param(["ABCD", "EFGH"], False, id="no-origin-2-vehicles"),
    pytest.param(["ABCDEFGHIJ"], False, id="no-origin-1-vehicle-long-route"),
    pytest.param(["AB", "CD"], False, id="no-origin-routes-of-2-cities"),
    pytest.param(["ABC", "DE"], False, id="no-origin-uneven-routes"),
]


class TestSegmentShuffleMutation:
    @pytest.mark.parametrize("routes, is_origin", INDIVIDUALS)
    def test_keeps_every_city_exactly_once(self, cities, routes, is_origin):
        for _ in range(100):
            individual = build(cities, *routes)
            mutated = mutate(individual, is_origin=is_origin)

            names_before = sorted(c["name"] for r in individual for c in r)
            names_after = sorted(c["name"] for r in mutated for c in r)
            assert names_after == names_before

    @pytest.mark.parametrize("routes, is_origin", INDIVIDUALS)
    def test_keeps_the_number_of_cities_per_vehicle(self, cities, routes, is_origin):
        for _ in range(100):
            mutated = mutate(build(cities, *routes), is_origin=is_origin)
            assert [len(route) for route in mutated] == [len(r) for r in routes]

    @pytest.mark.parametrize("routes, is_origin", INDIVIDUALS)
    def test_changes_the_order_of_a_single_vehicle(self, cities, routes, is_origin):
        for _ in range(100):
            individual = build(cities, *routes)
            mutated = mutate(individual, is_origin=is_origin)
            assert count_changed_routes(individual, mutated) == 1

    @pytest.mark.parametrize("routes, is_origin", INDIVIDUALS)
    def test_does_not_change_the_given_individual(self, cities, routes, is_origin):
        individual = build(cities, *routes)
        individual_before = copy.deepcopy(individual)

        for _ in range(100):
            mutate(individual, is_origin=is_origin)

        assert individual == individual_before

    @pytest.mark.parametrize(
        "routes", [["ABCD", "AEFG"], ["ABCDEFGHIJ"], ["AB", "AC", "ADEFG"]]
    )
    def test_origin_stays_at_the_start_of_every_route(self, cities, routes):
        for _ in range(100):
            mutated = mutate(build(cities, *routes), is_origin=True)
            assert all(route[0]["name"] == "A" for route in mutated)

    def test_shuffles_at_most_five_cities(self, cities):
        for _ in range(100):
            individual = build(cities, "ABCDEFGHIJ")
            mutated = mutate(individual, is_origin=False)

            moved = sum(
                city_before is not city_after
                for city_before, city_after in zip(individual[0], mutated[0])
            )
            assert 2 <= moved <= 5

    def test_no_mutation_when_probability_is_zero(self, cities):
        individual = build(cities, "ABCD", "AEFG")
        assert mutate(individual, mutation_probability=0.0) == individual

    def test_vehicle_with_a_single_client_is_never_mutated_when_there_is_origin(
        self, cities
    ):
        # [A, B] has only one city besides the origin: nothing to shuffle
        for _ in range(100):
            individual = build(cities, "AB", "ACDE")
            mutated = mutate(individual, is_origin=True)
            assert mutated[0] == individual[0]
            assert mutated[1] != individual[1]

    def test_returns_the_same_individual_when_no_vehicle_can_be_mutated(self, cities):
        individual = build(cities, "AB", "AC")
        assert mutate(individual, is_origin=True) == individual

    def test_route_of_two_cities_without_origin_is_swapped(self, cities):
        mutated = mutate(build(cities, "BC"), is_origin=False)
        assert route_names(mutated) == [["C", "B"]]

    def test_route_of_one_city_without_origin_is_not_mutated(self, cities):
        individual = build(cities, "B", "C")
        assert mutate(individual, is_origin=False) == individual

    def test_shuffles_the_chosen_segment_of_the_chosen_vehicle(self, cities):
        individual = build(cities, "ABCD", "AEFG")

        # picks the last vehicle, a segment of 2 cities starting at index 1
        # (E and F) and reverses it
        with patch("backend.ga.mutation.random.random", return_value=0.0), patch(
            "backend.ga.mutation.random.choice", side_effect=lambda seq: seq[-1]
        ), patch("backend.ga.mutation.random.randint", side_effect=[2, 1]), patch(
            "backend.ga.mutation.random.shuffle",
            side_effect=lambda items: items.reverse(),
        ):
            mutated = mutate(individual, is_origin=True)

        assert route_names(mutated) == [["A", "B", "C", "D"], ["A", "F", "E", "G"]]
