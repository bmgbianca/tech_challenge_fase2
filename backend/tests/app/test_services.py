from unittest.mock import patch

import pytest

from backend.app import services
from backend.models import GetOptimizedRouteArgs


def make_city(name, city_id, priority=False):
    return {
        "name": name,
        "id": city_id,
        "coordinates": [city_id, 0],
        "priority": priority,
    }


@pytest.fixture
def cities():
    # origin "A" has id 0, the other cities are the destinations
    return [make_city(name, index, name == "D") for index, name in enumerate("ABCDEFGH")]


@pytest.fixture
def run(cities):
    """Runs the whole GA with a small population, using a line-shaped
    distance matrix instead of calling OpenRouteService."""
    matrix = {
        (a["id"], b["id"]): 10.0 * abs(a["id"] - b["id"])
        for a in cities
        for b in cities
        if a is not b
    }

    def _run(origin_city, vehicles_number, population_type="random", pick=None):
        selected = cities if pick is None else pick
        with patch.object(
            services,
            "calculate_routes",
            return_value={"cities_distances": matrix, "cities_durations": matrix},
        ):
            return services.get_optimized_route(
                GetOptimizedRouteArgs(
                    cities=selected,
                    origin_city=origin_city,
                    population_type=population_type,
                    population_size=50,
                    mutation_probability=0.5,
                    max_generations=10,
                    plateau_window=5,
                    vehicles_number=vehicles_number,
                )
            )

    return _run


class TestGetRoutesNames:
    def test_returns_one_list_of_names_per_vehicle(self, cities):
        a, b, c, d = cities[:4]
        assert services.get_routes_names([[a, b, c], [a, d]]) == [
            ["A", "B", "C"],
            ["A", "D"],
        ]


class TestRunGeneticAlgorithm:
    @pytest.mark.parametrize("vehicles_number", [1, 2, 3])
    @pytest.mark.parametrize(
        "population_type", ["random", "nearest_neighbor", "cheapest_insertion"]
    )
    def test_with_origin_every_vehicle_starts_in_it(
        self, run, population_type, vehicles_number
    ):
        result = run("A", vehicles_number, population_type)

        routes = services.get_routes_names(result["best_solution"]["individual"])
        assert len(routes) == vehicles_number
        assert all(route[0] == "A" for route in routes)
        visited = sorted(name for route in routes for name in route[1:])
        assert visited == list("BCDEFGH")

    @pytest.mark.parametrize("vehicles_number", [1, 2, 3, 4])
    @pytest.mark.parametrize(
        "population_type", ["random", "nearest_neighbor", "cheapest_insertion"]
    )
    def test_without_origin_every_city_is_visited_exactly_once(
        self, run, population_type, vehicles_number
    ):
        result = run(None, vehicles_number, population_type)

        routes = services.get_routes_names(result["best_solution"]["individual"])
        assert len(routes) == vehicles_number
        visited = sorted(name for route in routes for name in route)
        assert visited == list("ABCDEFGH")

    def test_snapshots_store_one_route_per_vehicle(self, run):
        result = run(None, 2)

        for snapshot in result["snapshots"]:
            assert len(snapshot["route"]) == 2
            assert len(snapshot["second_best_route"]) == 2

    def test_more_vehicles_than_cities_to_visit_is_rejected(self, run, cities):
        with pytest.raises(ValueError):
            run("A", 8)

    def test_vehicles_number_equal_to_cities_to_visit_without_origin(self, run):
        result = run(None, 8)
        routes = services.get_routes_names(result["best_solution"]["individual"])
        assert all(len(route) == 1 for route in routes)


class TestGetVehiclesSummary:
    @pytest.fixture
    def routes(self):
        pairs = [(a, b) for a in range(5) for b in range(5) if a != b]
        return {
            "cities_distances": {(a, b): 10.0 * abs(a - b) for a, b in pairs},
            "cities_durations": {(a, b): 600.0 * abs(a - b) for a, b in pairs},
        }

    @pytest.fixture
    def cities(self):
        return [make_city(name, index) for index, name in enumerate("ABCDE")]

    def test_one_item_per_vehicle_with_its_own_numbers(self, cities, routes):
        a, b, c, d, e = cities

        summary = services.get_vehicles_summary([[a, b, c], [a, e]], routes, True)

        assert [item["vehicle"] for item in summary] == [1, 2]
        assert [item["route"] for item in summary] == [["A", "B", "C"], ["A", "E"]]
        assert [item["distance_km"] for item in summary] == [20.0, 40.0]
        assert [item["duration_seconds"] for item in summary] == [1200.0, 2400.0]

    def test_the_distances_add_up_to_the_fitness(self, cities, routes):
        a, b, c, d, e = cities
        individual = [[a, b, c], [a, d, e]]

        summary = services.get_vehicles_summary(individual, routes, True)

        assert sum(item["distance_km"] for item in summary) == services.calculate_fitness(
            routes["cities_distances"], individual
        )

    def test_fixed_origin_is_not_counted_as_a_stop(self, cities, routes):
        a, b, c, *_ = cities

        with_origin = services.get_vehicles_summary([[a, b, c]], routes, True)
        without_origin = services.get_vehicles_summary([[a, b, c]], routes, False)

        assert with_origin[0]["stops_count"] == 2
        assert without_origin[0]["stops_count"] == 3

    def test_priorities_are_checked_per_vehicle(self, routes):
        cities = [make_city(name, index, priority=(index == 4)) for index, name in enumerate("ABCDE")]
        a, b, c, d, e = cities

        # E is 4 steps from A (2400 s): on time with the default 17 h, late with 30 min
        on_time = services.get_vehicles_summary([[a, b], [a, e]], routes, True)
        with patch.object(services, "TIME_LIMIT", 1800):
            late = services.get_vehicles_summary([[a, b], [a, e]], routes, True)

        assert [i["priorities_on_time"] for i in on_time] == [True, True]
        assert [i["priorities_on_time"] for i in late] == [True, False]
        assert [i["priority_cities_count"] for i in on_time] == [0, 1]
