import json
from unittest.mock import patch

import pytest

from backend import demo


def make_city(name, city_id, priority=False):
    return {
        "name": name,
        "id": city_id,
        "coordinates": [str(city_id), "0"],
        "priority": priority,
    }


@pytest.fixture
def cities():
    return [make_city(name, index) for index, name in enumerate("ABCDE")]


@pytest.fixture
def routes():
    pairs = [(a, b) for a in range(5) for b in range(5) if a != b]
    return {
        "cities_distances": {(a, b): 10.0 * abs(a - b) for a, b in pairs},
        "cities_durations": {(a, b): 600.0 * abs(a - b) for a, b in pairs},
    }


class TestMatrixSerialization:
    def test_roundtrip_keeps_the_tuple_keys(self, routes):
        matrix = routes["cities_distances"]

        assert demo._deserialize_matrix(demo._serialize_matrix(matrix)) == matrix


class TestLoadDemoRoutes:
    def test_reads_the_matrices_from_the_cache_without_calling_ors(
        self, cities, routes, tmp_path
    ):
        cache_file = tmp_path / "demo_routes.json"
        cache_file.write_text(
            json.dumps(
                {
                    "coordinates": [city["coordinates"] for city in cities],
                    "cities_distances": demo._serialize_matrix(
                        routes["cities_distances"]
                    ),
                    "cities_durations": demo._serialize_matrix(
                        routes["cities_durations"]
                    ),
                }
            )
        )

        with patch.object(demo, "calculate_routes") as calculate:
            loaded = demo.load_demo_routes(cities, cache_file, dataset=cities)

        assert loaded == routes
        calculate.assert_not_called()

    def test_requests_and_caches_the_matrices_when_there_is_no_cache(
        self, cities, routes, tmp_path
    ):
        cache_file = tmp_path / "demo_routes.json"

        with patch.dict(demo.os.environ, {"OPENROUTESERVICE_API_KEY": "real-key"}):
            with patch.object(demo, "calculate_routes", return_value=routes) as calc:
                first = demo.load_demo_routes(cities, cache_file, dataset=cities)
                second = demo.load_demo_routes(cities, cache_file, dataset=cities)

        assert first == second == routes
        calc.assert_called_once()

    def test_a_subset_of_the_dataset_is_served_from_the_cache_without_overwriting_it(
        self, cities, routes, tmp_path
    ):
        cache_file = tmp_path / "demo_routes.json"
        with patch.dict(demo.os.environ, {"OPENROUTESERVICE_API_KEY": "real-key"}):
            with patch.object(demo, "calculate_routes", return_value=routes) as calc:
                demo.load_demo_routes(cities, cache_file, dataset=cities)
                content = cache_file.read_text()
                subset = demo.load_demo_routes(cities[:3], cache_file, dataset=cities)

        calc.assert_called_once()
        assert cache_file.read_text() == content
        assert set(subset["cities_distances"]) == {
            (a, b) for a in range(3) for b in range(3) if a != b
        }

    def test_cache_for_other_coordinates_is_ignored(self, cities, routes, tmp_path):
        cache_file = tmp_path / "demo_routes.json"
        cache_file.write_text(
            json.dumps(
                {"coordinates": [["9", "9"]], "cities_distances": {}, "cities_durations": {}}
            )
        )

        with patch.dict(demo.os.environ, {"OPENROUTESERVICE_API_KEY": "real-key"}):
            with patch.object(demo, "calculate_routes", return_value=routes) as calc:
                demo.load_demo_routes(cities, cache_file, dataset=cities)

        calc.assert_called_once()

    def test_without_cache_and_without_key_it_explains_what_to_do(
        self, cities, tmp_path
    ):
        with patch.dict(demo.os.environ, {"OPENROUTESERVICE_API_KEY": "offline-demo"}):
            with pytest.raises(RuntimeError, match="OPENROUTESERVICE_API_KEY"):
                demo.load_demo_routes(
                    cities, tmp_path / "demo_routes.json", dataset=cities
                )


class TestRunDemo:
    @pytest.fixture
    def run(self, cities, routes):
        def run(**kwargs):
            with patch.object(demo, "load_demo_routes", return_value=routes):
                return demo.run_demo(
                    cities=cities,
                    origin="A",
                    population_size=50,
                    max_generations=20,
                    plateau_window=10,
                    **kwargs,
                )

        return run

    def test_same_seed_gives_the_same_result(self, run):
        first = run(vehicles_number=2, seed=3)
        second = run(vehicles_number=2, seed=3)

        assert first["fitness_history"] == second["fitness_history"]
        assert get_names(first) == get_names(second)

    def test_every_vehicle_starts_in_the_origin_and_all_cities_are_served(self, run):
        result = run(vehicles_number=2, seed=1)

        routes = get_names(result)
        assert len(routes) == 2
        assert all(route[0] == "A" for route in routes)
        assert {name for route in routes for name in route} == set("ABCDE")

    def test_does_not_call_openroute_service_when_the_matrices_are_given(
        self, cities, routes
    ):
        with patch.object(demo, "load_demo_routes", return_value=routes), patch(
            "backend.app.services.calculate_routes"
        ) as calculate:
            demo.run_demo(
                cities=cities, origin="A", population_size=50,
                max_generations=5, plateau_window=3, vehicles_number=2,
            )

        calculate.assert_not_called()

    def test_summary_has_one_block_per_vehicle(self, run):
        summary = demo.format_summary(run(vehicles_number=2, seed=1))

        assert "Veículo 1" in summary and "Veículo 2" in summary
        assert "Veículo 3" not in summary
        assert "Distância total" in summary
        assert "Prioridades dentro do prazo" in summary

    def test_vehicle_summaries_add_up_to_the_total_distance(self, run):
        result = run(vehicles_number=2, seed=1)

        total = sum(v["distance_km"] for v in demo.vehicle_summaries(result))
        assert total == pytest.approx(result["best_solution"]["total_distance"])


class TestFormatDuration:
    def test_hours_and_minutes(self):
        assert demo.format_duration(3 * 3600 + 5 * 60) == "3h05min"


def get_names(result):
    return [[city["name"] for city in vehicle] for vehicle in result["best_solution"]["individual"]]
