from unittest.mock import patch

import pytest

from backend import baselines


def make_city(name, city_id, priority=False):
    return {"name": name, "id": city_id, "coordinates": [str(city_id), "0"], "priority": priority}


@pytest.fixture
def cities():
    return [make_city(name, index) for index, name in enumerate("ABCDEF")]


@pytest.fixture
def routes():
    """Cities on a line: distance 10 km and 10 min per id of difference."""
    pairs = [(a, b) for a in range(6) for b in range(6) if a != b]
    return {
        "cities_distances": {(a, b): 10.0 * abs(a - b) for a, b in pairs},
        "cities_durations": {(a, b): 600.0 * abs(a - b) for a, b in pairs},
    }


def names(individual):
    return [[city["name"] for city in vehicle] for vehicle in individual]


class TestEvaluate:
    def test_returns_distance_duration_and_deadline(self, cities, routes):
        a, b, c = cities[:3]

        result = baselines.evaluate(routes, [[a, b], [a, c]])

        assert result["distance_km"] == 30.0
        assert result["duration_seconds"] == 1200.0
        assert result["priorities_on_time"] is True


class TestGreedyNearestNeighbor:
    def test_goes_to_the_closest_city_every_time(self, cities, routes):
        individual = baselines.greedy_nearest_neighbor(routes, cities, "A", 1)

        assert names(individual) == [["A", "B", "C", "D", "E", "F"]]

    def test_is_deterministic(self, cities, routes):
        first = baselines.greedy_nearest_neighbor(routes, cities, "A", 2)
        second = baselines.greedy_nearest_neighbor(routes, cities, "A", 2)

        assert first == second


class TestBestOfRandom:
    def test_returns_a_solution_that_serves_every_city_once(self, cities, routes):
        individual = baselines.best_of_random(routes, cities, "A", 2, samples=50)

        served = [name for vehicle in names(individual) for name in vehicle[1:]]
        assert sorted(served) == list("BCDEF")
        assert all(vehicle[0] == "A" for vehicle in names(individual))

    def test_more_samples_never_give_a_worse_best(self, cities, routes):
        import random

        random.seed(1)
        few = baselines.best_of_random(routes, cities, "A", 2, samples=5)
        random.seed(1)
        many = baselines.best_of_random(routes, cities, "A", 2, samples=300)

        assert baselines.evaluate(routes, many)["distance_km"] <= baselines.evaluate(
            routes, few
        )["distance_km"]


class TestExhaustiveSearch:
    def test_single_vehicle_optimum_on_a_line_is_the_straight_path(self, cities, routes):
        individual, tried = baselines.exhaustive_search(routes, cities, "A", 1)

        assert names(individual) == [["A", "B", "C", "D", "E", "F"]]
        assert tried == 120  # 5! orders

    def test_balanced_split_keeps_the_ga_sizes(self, cities, routes):
        individual, tried = baselines.exhaustive_search(routes, cities, "A", 2)

        # 5 cities in 2 vehicles: 3 + 2 (the remainder goes to the first vehicle)
        assert [len(vehicle) - 1 for vehicle in individual] == [3, 2]
        assert tried == 120

    def test_free_split_tries_every_cut_and_is_never_worse(self, cities, routes):
        balanced, _ = baselines.exhaustive_search(routes, cities, "A", 2, balanced=True)
        free, tried = baselines.exhaustive_search(routes, cities, "A", 2, balanced=False)

        assert tried == 120 * 4  # 5! orders x 4 ways to cut into two non-empty routes
        assert baselines.evaluate(routes, free)["distance_km"] <= baselines.evaluate(
            routes, balanced
        )["distance_km"]
        assert all(len(vehicle) > 1 for vehicle in free)

    def test_prefers_solutions_that_meet_the_deadline(self, routes):
        cities = [make_city(name, index, priority=(index == 5)) for index, name in enumerate("ABCDEF")]
        # F is a priority city 5 hours away from A; with a 2h deadline no solution
        # can meet it, so the shortest solution overall is returned
        with patch.object(baselines, "TIME_LIMIT", 2 * 3600):
            individual, _ = baselines.exhaustive_search(routes, cities, "A", 1)

        assert baselines.evaluate(routes, individual)["distance_km"] == 50.0
