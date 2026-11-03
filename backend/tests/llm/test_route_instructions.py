import json
from unittest.mock import MagicMock, patch

import pytest

from backend.llm import route_instructions
from backend.llm.route_instructions import (
    generate_driver_instructions,
    prepare_route_data,
)


def make_city(name, city_id):
    return {"name": name, "id": city_id}


@pytest.fixture
def cities():
    return {name: make_city(name, index) for index, name in enumerate("ABCD")}


@pytest.fixture
def calculated_routes():
    # cities lie on a line: 1000 km and 1 hour (3600 s) per id of difference
    pairs = [(a, b) for a in range(4) for b in range(4) if a != b]
    return {
        "cities_distances": {(a, b): 1000.0 * abs(a - b) for a, b in pairs},
        "cities_durations": {(a, b): 3600.0 * abs(a - b) for a, b in pairs},
    }


def stretches(data):
    return [vehicle["stretches"] for vehicle in data]


def prepare(calculated_routes, individual):
    """Runs prepare_route_data returning the data that would be sent to the
    LLM, without calling it."""
    with patch.object(
        route_instructions, "generate_driver_instructions", side_effect=lambda d: d
    ):
        return prepare_route_data(calculated_routes, {"individual": individual})


class TestPrepareRouteData:
    def test_returns_one_item_with_stretches_per_vehicle(self, cities, calculated_routes):
        a, b, c, d = (cities[name] for name in "ABCD")

        data = prepare(calculated_routes, [[a, b, c], [a, d]])

        assert len(data) == 2
        assert [[s["cities"] for s in vehicle] for vehicle in stretches(data)] == [
            [["A", "B"], ["B", "C"]],
            [["A", "D"]],
        ]

    def test_each_vehicle_has_one_stretch_less_than_cities(
        self, cities, calculated_routes
    ):
        a, b, c, d = (cities[name] for name in "ABCD")

        data = prepare(calculated_routes, [[a, b, c, d]])

        assert len(data) == 1
        assert len(data[0]["stretches"]) == 3

    def test_stretch_has_distance_and_duration_in_hours_and_minutes(
        self, cities, calculated_routes
    ):
        a, _, c, _ = (cities[name] for name in "ABCD")
        calculated_routes["cities_durations"][(0, 2)] = 2 * 3600 + 30 * 60

        data = prepare(calculated_routes, [[a, c]])

        assert data[0]["stretches"][0] == {
            "cities": ["A", "C"],
            "distance_km": 2000.0,
            "duration": (2.0, 30.0),
        }

    def test_total_duration_sums_the_stretches_of_each_vehicle(
        self, cities, calculated_routes
    ):
        a, b, c, d = (cities[name] for name in "ABCD")
        # A->B 1h, B->D 2h, A->C 2h
        data = prepare(calculated_routes, [[a, b, d], [a, c]])

        assert [vehicle["total_duration"] for vehicle in data] == [(3.0, 0.0), (2.0, 0.0)]

    def test_total_duration_sums_seconds_before_converting(
        self, cities, calculated_routes
    ):
        a, b, c, _ = (cities[name] for name in "ABCD")
        # two stretches of 40 min each: 80 min = 1h20, not 0h40 + 0h40
        calculated_routes["cities_durations"][(0, 1)] = 40 * 60
        calculated_routes["cities_durations"][(1, 2)] = 40 * 60

        data = prepare(calculated_routes, [[a, b, c]])

        assert data[0]["total_duration"] == (1.0, 20.0)

    def test_stretches_follow_the_order_of_the_route(self, cities, calculated_routes):
        a, b, c, d = (cities[name] for name in "ABCD")

        data = prepare(calculated_routes, [[a, d, b, c]])

        assert [s["cities"] for s in data[0]["stretches"]] == [["A", "D"], ["D", "B"], ["B", "C"]]

    def test_route_is_open_and_does_not_return_to_origin(
        self, cities, calculated_routes
    ):
        a, b, c, _ = (cities[name] for name in "ABCD")

        data = prepare(calculated_routes, [[a, b, c]])

        assert ["C", "A"] not in [s["cities"] for s in data[0]["stretches"]]

    def test_vehicle_with_only_the_origin_has_no_stretches(
        self, cities, calculated_routes
    ):
        a, b, _, _ = (cities[name] for name in "ABCD")

        data = prepare(calculated_routes, [[a], [a, b]])

        assert data[0] == {"stretches": [], "total_duration": (0, 0)}
        assert len(data[1]["stretches"]) == 1

    @pytest.mark.parametrize("missing_matrix", ["cities_distances", "cities_durations"])
    def test_raises_when_a_stretch_is_missing_from_the_matrices(
        self, cities, calculated_routes, missing_matrix
    ):
        a, b, c, _ = (cities[name] for name in "ABCD")
        del calculated_routes[missing_matrix][(1, 2)]

        with pytest.raises(ValueError, match="B -> C"):
            prepare(calculated_routes, [[a, b, c]])

    def test_sends_the_data_to_generate_driver_instructions(
        self, cities, calculated_routes
    ):
        a, b, _, _ = (cities[name] for name in "ABCD")

        with patch.object(
            route_instructions,
            "generate_driver_instructions",
            return_value="instruções",
        ) as generate:
            result = prepare_route_data(calculated_routes, {"individual": [[a, b]]})

        assert result == "instruções"
        generate.assert_called_once_with(
            [
                {
                    "stretches": [
                        {
                            "cities": ["A", "B"],
                            "distance_km": 1000.0,
                            "duration": (1.0, 0.0),
                        }
                    ],
                    "total_duration": (1.0, 0.0),
                }
            ]
        )


class TestGenerateDriverInstructions:
    @pytest.fixture
    def llm(self):
        with patch.object(route_instructions, "LLMClient") as llm_class:
            llm_class.return_value = MagicMock()
            llm_class.return_value.generate_response.return_value = "texto da LLM"
            yield llm_class.return_value

    @pytest.fixture
    def data(self):
        return [
            {
                "stretches": [
                    {"cities": ["São Paulo", "Campinas"], "distance_km": 95.5, "duration": (1, 10)}
                ],
                "total_duration": (1, 10),
            },
            {
                "stretches": [
                    {"cities": ["São Paulo", "Santos"], "distance_km": 72.0, "duration": (1, 0)}
                ],
                "total_duration": (1, 0),
            },
        ]

    def test_returns_the_text_generated_by_the_llm(self, llm, data):
        assert generate_driver_instructions(data) == "texto da LLM"

    def test_prompt_contains_the_data_of_every_vehicle_as_json(self, llm, data):
        generate_driver_instructions(data)

        prompt = llm.generate_response.call_args.kwargs["prompt"]
        assert "São Paulo" in prompt and "Campinas" in prompt and "Santos" in prompt
        assert json.loads(prompt[prompt.index("[") :]) == json.loads(
            json.dumps(data)
        )

    def test_instructions_explain_multiple_vehicles_and_open_routes(self, llm, data):
        generate_driver_instructions(data)

        instructions = llm.generate_response.call_args.kwargs["instructions"]
        assert "um para cada veículo" in instructions
        assert "abertas" in instructions
        assert "volta" in instructions

    def test_instructions_ask_for_numbered_texts_and_provided_total_duration(self, llm, data):
        generate_driver_instructions(data)

        instructions = llm.generate_response.call_args.kwargs["instructions"]
        assert "[1]" in instructions and "[2]" in instructions
        assert "total_duration" in instructions
        assert "Nunca" in instructions and "calcule" in instructions

    def test_instructions_cover_routes_without_a_fixed_origin(self, llm, data):
        generate_driver_instructions(data)

        instructions = llm.generate_response.call_args.kwargs["instructions"]
        assert "nem sempre há uma origem fixa" in instructions
        assert "primeira cidade dos seus stretches" in instructions
        assert "Não presuma" in instructions

    def test_calls_the_llm_once(self, llm, data):
        generate_driver_instructions(data)
        llm.generate_response.assert_called_once()
