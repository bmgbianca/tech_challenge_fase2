import pytest

from backend.ga import (
    are_priorities_on_time,
    calculate_fitness,
    calculate_solution_duration,
    get_distance,
)


def make_city(name, city_id, priority=False):
    return {"name": name, "id": city_id, "priority": priority}


@pytest.fixture
def cities():
    return [make_city(name, index) for index, name in enumerate("ABCD")]


@pytest.fixture
def matrix(cities):
    # cities lie on a line, 10 units apart: distance (or duration) between
    # two cities is 10 * the difference between their ids
    return {
        (city_a["id"], city_b["id"]): 10.0 * abs(city_a["id"] - city_b["id"])
        for city_a in cities
        for city_b in cities
        if city_a is not city_b
    }


class TestCalculateFitness:
    def test_single_vehicle_sums_distance_along_route(self, cities, matrix):
        a, b, c, d = cities
        assert calculate_fitness(matrix, [[a, b, c, d]]) == 30.0

    def test_sums_the_distance_of_all_vehicles(self, cities, matrix):
        a, b, c, d = cities
        # A->B->C = 20 and A->D = 30
        assert calculate_fitness(matrix, [[a, b, c], [a, d]]) == 50.0

    def test_vehicle_with_a_single_city_has_zero_distance(self, cities, matrix):
        a, b, _, _ = cities
        assert calculate_fitness(matrix, [[a], [a, b]]) == 10.0


class TestGetDistance:
    def test_returns_known_distance(self, matrix):
        assert get_distance(matrix, 0, 1) == 10.0

    def test_raises_for_unknown_pair(self, matrix):
        with pytest.raises(KeyError):
            get_distance(matrix, 99, 100)


class TestCalculateSolutionDuration:
    def test_single_vehicle_sums_the_duration_of_the_route(self, cities, matrix):
        a, b, c, d = cities
        assert calculate_solution_duration(matrix, [[a, b, c, d]]) == 30.0

    def test_returns_the_duration_of_the_slowest_vehicle(self, cities, matrix):
        a, b, c, d = cities
        # vehicles run in parallel: A->B->C = 20 and A->D = 30
        assert calculate_solution_duration(matrix, [[a, b, c], [a, d]]) == 30.0


class TestArePrioritiesOnTime:
    def test_true_when_there_is_no_priority_city(self, cities, matrix):
        a, b, c, d = cities
        assert are_priorities_on_time(matrix, [[a, b], [a, c, d]], 1) is True

    def test_true_when_every_priority_city_is_within_the_time_limit(
        self, cities, matrix
    ):
        a, b, c, d = cities
        c["priority"] = True  # reached after 20
        d["priority"] = True  # reached after 30
        assert are_priorities_on_time(matrix, [[a, b, c], [a, d]], 30) is True

    def test_false_when_one_vehicle_reaches_its_priority_city_too_late(
        self, cities, matrix
    ):
        a, b, c, d = cities
        c["priority"] = True  # reached after 20 (ok)
        d["priority"] = True  # reached after 30 (too late)
        assert are_priorities_on_time(matrix, [[a, b, c], [a, d]], 25) is False

    def test_ignores_the_route_after_the_last_priority_city(self, cities, matrix):
        a, b, c, d = cities
        b["priority"] = True  # reached after 10; B->C->D (20 more) doesn't count
        assert are_priorities_on_time(matrix, [[a, b, c, d]], 10) is True

    def test_vehicle_without_priority_city_never_breaks_the_limit(
        self, cities, matrix
    ):
        a, b, c, d = cities
        b["priority"] = True
        # second vehicle takes 30 but has no priority city
        assert are_priorities_on_time(matrix, [[a, b], [a, d]], 10) is True
