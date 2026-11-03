import importlib
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from backend.app import history

# backend.app re-exports the Blueprint as "routes", which hides the module
routes_module = importlib.import_module("backend.app.routes")
routes = routes_module.routes


def make_city(name, city_id):
    return {"name": name, "id": city_id, "coordinates": [city_id, 0], "priority": False}


@pytest.fixture
def history_file(tmp_path):
    file = tmp_path / "route_runs.json"
    with patch.object(history, "HISTORY_FILE", file):
        yield file


@pytest.fixture
def client():
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(routes)
    return app.test_client()


@pytest.fixture
def payload():
    return {
        "population_type": "random",
        "population_size": 50,
        "mutation_probability": 0.5,
        "vehicles_number": 2,
        "origin_city": make_city("A", 0),
        "destination_cities": [make_city(name, i) for i, name in enumerate("BCDE", 1)],
    }


@pytest.fixture
def fake_result():
    a, b, c, d, e = (make_city(name, i) for i, name in enumerate("ABCDE"))
    return {
        "best_solution": {
            "individual": [[a, b, c], [a, d, e]],
            "total_distance": 42.0,
            "priorities_on_time": True,
        },
        "total_duration": 100.0,
        "fitness_history": [50.0, 42.0],
        "snapshots": [],
        # cities on a line: 10 km and 600 s per id of difference
        "calculated_routes": {
            "cities_distances": {(a, b): 10.0 * abs(a - b) for a in range(5) for b in range(5) if a != b},
            "cities_durations": {(a, b): 600.0 * abs(a - b) for a in range(5) for b in range(5) if a != b},
        },
    }


def body_is_ok(response):
    return response.get_json().get("best_route") is not None


class TestSaveRouteRun:
    def test_stores_routes_per_vehicle_and_distinct_city_set(self, history_file):
        run = history.save_route_run(
            population_type="random",
            population_size=50,
            mutation_probability=0.5,
            best_distance=42.0,
            total_duration=100.0,
            priorities_on_time=True,
            stops_count=5,
            vehicles_number=2,
            best_route=[["A", "B", "C"], ["A", "D", "E"]],
            generations_run=2,
        )

        assert run["best_route"] == [["A", "B", "C"], ["A", "D", "E"]]
        assert run["city_set"] == ["A", "B", "C", "D", "E"]
        assert run["vehicles_number"] == 2
        assert json.loads(history_file.read_text())[0]["id"] == run["id"]


class TestOptimizeRoute:
    def test_returns_and_saves_one_route_per_vehicle(
        self, client, payload, fake_result, history_file
    ):
        with patch.object(routes_module, "get_optimized_route", return_value=fake_result):
            response = client.post("/api/optimized-route", json=payload)

        body = response.get_json()
        assert response.status_code == 200
        assert body["best_route"] == [["A", "B", "C"], ["A", "D", "E"]]
        assert body["stops_count"] == 5
        assert body["vehicles_number"] == 2
        assert [city["name"] for city in body["cities"]] == list("BCDEA")
        assert [v["route"] for v in body["vehicles_summary"]] == body["best_route"]
        assert [v["distance_km"] for v in body["vehicles_summary"]] == [20.0, 40.0]

        saved = history.get_route_runs()[0]
        assert saved["best_route"] == body["best_route"]
        assert saved["city_set"] == ["A", "B", "C", "D", "E"]

    def test_passes_vehicles_number_to_the_algorithm(
        self, client, payload, fake_result, history_file
    ):
        with patch.object(
            routes_module, "get_optimized_route", return_value=fake_result
        ) as get_optimized_route:
            client.post("/api/optimized-route", json=payload)

        args = get_optimized_route.call_args.args[0]
        assert args.vehicles_number == 2
        assert args.origin_city == "A"

    @pytest.mark.parametrize("origin_city", [None, "", "missing"])
    def test_works_without_origin_city(
        self, client, payload, fake_result, history_file, origin_city
    ):
        if origin_city == "missing":
            del payload["origin_city"]
        else:
            payload["origin_city"] = origin_city

        with patch.object(
            routes_module, "get_optimized_route", return_value=fake_result
        ) as get_optimized_route:
            response = client.post("/api/optimized-route", json=payload)

        assert response.status_code == 200
        args = get_optimized_route.call_args.args[0]
        assert args.origin_city is None
        assert len(args.cities) == 4
        assert body_is_ok(response)

    def test_missing_vehicles_number_is_a_bad_request(self, client, payload):
        del payload["vehicles_number"]
        response = client.post("/api/optimized-route", json=payload)
        assert response.status_code == 400
        assert "vehicles_number" in response.get_json()["error"]

    def test_invalid_vehicles_number_becomes_a_bad_request(self, client, payload):
        with patch.object(
            routes_module, "get_optimized_route", side_effect=ValueError("veículos")
        ):
            response = client.post("/api/optimized-route", json=payload)
        assert response.status_code == 400


class TestDriverInstructions:
    @pytest.fixture
    def chosen_cities(self):
        # cities chosen by the user: none of them is in the fixed demo dataset
        return [make_city(name, index) for index, name in enumerate(["Atlantis", "Gotham", "Narnia"])]

    @pytest.fixture
    def ask(self, client, chosen_cities):
        def _ask(route, cities="default"):
            body = {"route": route}
            body["cities"] = chosen_cities if cities == "default" else cities
            with patch.object(
                routes_module, "prepare_route_data", return_value="ok"
            ) as prepare, patch.object(
                routes_module, "calculate_routes", return_value={}
            ) as calculate:
                response = client.post("/api/driver-instructions", json=body)
            return response, prepare, calculate

        return _ask

    def test_works_with_cities_that_are_not_in_the_demo_dataset(self, ask):
        response, prepare, _ = ask([["Atlantis", "Gotham"], ["Atlantis", "Narnia"]])

        assert response.status_code == 200
        individual = prepare.call_args.args[1]["individual"]
        assert [[city["name"] for city in route] for route in individual] == [
            ["Atlantis", "Gotham"],
            ["Atlantis", "Narnia"],
        ]

    def test_flat_list_of_names_is_a_single_vehicle(self, ask):
        _, prepare, _ = ask(["Atlantis", "Gotham"])

        assert len(prepare.call_args.args[1]["individual"]) == 1

    def test_distances_are_calculated_only_for_the_cities_of_the_route(self, ask):
        _, _, calculate = ask([["Atlantis", "Gotham"]])

        calculated_cities = calculate.call_args.args[0]
        assert sorted(city["name"] for city in calculated_cities) == [
            "Atlantis",
            "Gotham",
        ]

    def test_city_shared_by_vehicles_is_calculated_once(self, ask):
        _, _, calculate = ask([["Atlantis", "Gotham"], ["Atlantis", "Narnia"]])

        assert len(calculate.call_args.args[0]) == 3

    def test_city_of_the_route_missing_from_cities_is_a_bad_request(self, ask):
        response, _, _ = ask([["Atlantis", "Eldorado"]])

        assert response.status_code == 400
        assert "Eldorado" in response.get_json()["error"]

    def test_cities_are_required(self, ask):
        response, _, _ = ask([["Atlantis", "Gotham"]], cities=None)
        assert response.status_code == 400

    def test_route_is_required(self, client, chosen_cities):
        response = client.post("/api/driver-instructions", json={"cities": chosen_cities})
        assert response.status_code == 400

    def test_failure_generating_instructions_is_a_server_error(self, client, chosen_cities):
        with patch.object(
            routes_module, "prepare_route_data", side_effect=RuntimeError("falhou")
        ), patch.object(routes_module, "calculate_routes", return_value={}):
            response = client.post(
                "/api/driver-instructions",
                json={"route": [["Atlantis", "Gotham"]], "cities": chosen_cities},
            )
        assert response.status_code == 500


class TestSearchCities:
    @pytest.fixture
    def municipalities(self):
        return [
            {"id": 1, "name": "São Paulo"},
            {"id": 2, "name": "São José dos Campos"},
            {"id": 3, "name": "Araçatuba"},
            {"id": 4, "name": "Campinas"},
        ]

    def search(self, client, municipalities, query):
        with patch.object(
            routes_module, "get_sp_municipalities", return_value=municipalities
        ):
            response = client.get("/api/cities/search", query_string={"q": query})
        assert response.status_code == 200
        return [city["name"] for city in response.get_json()]

    @pytest.mark.parametrize("query", ["sao", "SAO", "São", "são", "sÃo"])
    def test_ignores_accents_and_case(self, client, municipalities, query):
        assert self.search(client, municipalities, query) == [
            "São Paulo",
            "São José dos Campos",
        ]

    def test_accented_names_are_found_without_the_accent(self, client, municipalities):
        assert self.search(client, municipalities, "aracatuba") == ["Araçatuba"]
        assert self.search(client, municipalities, "araçatuba") == ["Araçatuba"]

    def test_matches_inside_the_name(self, client, municipalities):
        assert self.search(client, municipalities, "jose dos") == ["São José dos Campos"]

    def test_short_query_returns_nothing(self, client, municipalities):
        assert self.search(client, municipalities, "s") == []
        assert self.search(client, municipalities, " ") == []

    def test_unknown_city_returns_nothing(self, client, municipalities):
        assert self.search(client, municipalities, "atlantis") == []


class TestComparativeReport:
    @pytest.fixture
    def stored_runs(self, history_file):
        now = datetime.now(timezone.utc)

        def run(run_id, vehicles, days_ago):
            return {
                "id": run_id,
                "created_at": (now - timedelta(days=days_ago)).isoformat(),
                "best_route": [["A", "B"]] * vehicles,
                "city_set": ["A", "B"],
                "vehicles_number": vehicles,
            }

        history_file.write_text(
            json.dumps(
                [run("r1", 2, 0.5), run("r2", 2, 3), run("r3", 2, 20), run("r4", 3, 0.5)]
            )
        )

    @pytest.fixture
    def generate(self, stored_runs, tmp_path):
        with patch.object(
            routes_module, "generate_comparative_report", return_value="texto"
        ) as generate, patch.object(
            routes_module, "get_cached_report", return_value=None
        ), patch.object(routes_module, "save_report"):
            yield generate

    def post(self, client, **body):
        return client.post(
            "/api/route-runs/comparative-report", json={"city_set": ["A", "B"], **body}
        )

    def sent_ids(self, generate):
        return [run["id"] for run in generate.call_args.args[0]]

    def test_only_runs_with_the_same_vehicles_number_are_compared(self, client, generate):
        assert self.post(client, vehicles_number=2).status_code == 200
        assert self.sent_ids(generate) == ["r1", "r2", "r3"]

    def test_day_period_keeps_only_the_last_24_hours(self, client, generate):
        self.post(client, vehicles_number=2, period="day")
        assert self.sent_ids(generate) == ["r1"]
        assert generate.call_args.args[1] == "day"

    def test_week_period(self, client, generate):
        self.post(client, vehicles_number=2, period="week")
        assert self.sent_ids(generate) == ["r1", "r2"]

    def test_404_when_no_run_matches(self, client, generate):
        assert self.post(client, vehicles_number=5).status_code == 404

    def test_400_for_invalid_period(self, client, generate):
        assert self.post(client, vehicles_number=2, period="month").status_code == 400

    def test_cache_key_depends_on_the_period(self, client, stored_runs):
        with patch.object(
            routes_module, "generate_comparative_report", return_value="x"
        ), patch.object(routes_module, "get_cached_report", return_value=None) as get, patch.object(
            routes_module, "save_report"
        ):
            self.post(client, vehicles_number=2, period="week")
            self.post(client, vehicles_number=2, period="all")

        keys = [call.args[0] for call in get.call_args_list]
        assert keys[0] != keys[1]


class TestProcessRecommendations:
    RUNS = [{"id": "r1", "best_route": [["A"]]}, {"id": "r2", "best_route": [["A"]]}]

    @pytest.fixture
    def cache(self):
        with patch.object(
            routes_module, "get_cached_report", return_value=None
        ) as get, patch.object(routes_module, "save_report") as save:
            yield get, save

    def post(self, client):
        return client.post("/api/process-recommendations")

    def test_404_when_there_is_no_history(self, client, cache):
        with patch.object(routes_module, "get_route_runs", return_value=[]):
            response = self.post(client)

        assert response.status_code == 404

    def test_generates_and_caches_the_report(self, client, cache):
        _, save = cache

        with patch.object(
            routes_module, "get_route_runs", return_value=self.RUNS
        ), patch.object(
            routes_module, "generate_process_recommendations", return_value="texto"
        ) as generate:
            response = self.post(client)

        assert response.get_json() == {"report": "texto", "cached": False}
        generate.assert_called_once_with(self.RUNS)
        save.assert_called_once_with("global:r1|r2", "texto", ["r1", "r2"])

    def test_uses_the_cached_report_without_calling_the_llm(self, client, cache):
        get, _ = cache
        get.return_value = {"report": "salvo"}

        with patch.object(
            routes_module, "get_route_runs", return_value=self.RUNS
        ), patch.object(routes_module, "generate_process_recommendations") as generate:
            response = self.post(client)

        assert response.get_json() == {"report": "salvo", "cached": True}
        generate.assert_not_called()

    def test_500_when_the_llm_fails(self, client, cache):
        with patch.object(
            routes_module, "get_route_runs", return_value=self.RUNS
        ), patch.object(
            routes_module,
            "generate_process_recommendations",
            side_effect=RuntimeError("falhou"),
        ):
            response = self.post(client)

        assert response.status_code == 500
        assert response.get_json() == {"error": "falhou"}


class TestGeocodeCities:
    def post(self, client, **body):
        return client.post("/api/geocode-cities", json=body)

    def test_400_without_cities(self, client):
        assert self.post(client).status_code == 400
        assert self.post(client, cities=[]).status_code == 400

    def test_returns_the_coordinates_by_name(self, client):
        with patch.object(
            routes_module, "geocode_cities", return_value={"Campinas": [1.0, 2.0]}
        ) as geocode:
            response = self.post(client, cities=["Campinas"])

        assert response.get_json() == {"coordinates": {"Campinas": [1.0, 2.0]}}
        geocode.assert_called_once_with(["Campinas"])

    def test_400_for_an_unknown_city(self, client):
        with patch.object(
            routes_module, "geocode_cities", side_effect=ValueError("não encontrado")
        ):
            response = self.post(client, cities=["Atlantis"])

        assert response.status_code == 400
        assert response.get_json() == {"error": "não encontrado"}

    def test_500_for_an_unexpected_failure(self, client):
        with patch.object(
            routes_module, "geocode_cities", side_effect=RuntimeError("IBGE fora")
        ):
            response = self.post(client, cities=["Campinas"])

        assert response.status_code == 500
