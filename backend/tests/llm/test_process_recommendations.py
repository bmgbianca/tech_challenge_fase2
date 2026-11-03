import json
from unittest.mock import MagicMock, patch

import pytest

from backend.llm import process_recommendations
from backend.llm.process_recommendations import (
    generate_process_recommendations,
    prepare_process_recommendations_data,
)


def make_run(created_at, **overrides):
    run = {
        "id": created_at,
        "created_at": created_at,
        "population_type": "random",
        "population_size": 100,
        "mutation_probability": 0.5,
        "generations_run": 10,
        "best_distance": 123.456,
        "total_duration": 5400,
        "best_route": [["A", "B"], ["A", "C"]],
        "city_set": ["A", "B", "C"],
        "vehicles_number": 2,
    }
    run.update(overrides)
    return run


class TestPrepareProcessRecommendationsData:
    def test_runs_are_sorted_from_oldest_to_newest(self):
        data = prepare_process_recommendations_data(
            [make_run("2026-03-01"), make_run("2026-01-01"), make_run("2026-02-01")]
        )

        assert [item["date"] for item in data] == [
            "2026-01-01",
            "2026-02-01",
            "2026-03-01",
        ]

    def test_keeps_only_the_fields_relevant_for_the_analysis(self):
        data = prepare_process_recommendations_data([make_run("2026-01-01")])

        assert data == [
            {
                "date": "2026-01-01",
                "city_set_size": 3,
                "vehicles_number": 2,
                "population_type": "random",
                "population_size": 100,
                "mutation_probability": 0.5,
                "generations_run": 10,
                "distance_km": 123.5,
                "duration": (1.0, 30.0),
            }
        ]

    def test_city_names_are_not_sent(self):
        data = prepare_process_recommendations_data([make_run("2026-01-01")])

        assert "best_route" not in data[0] and "city_set" not in data[0]

    def test_legacy_run_without_vehicles_number_counts_as_one_vehicle(self):
        run = make_run("2026-01-01")
        del run["vehicles_number"]

        assert prepare_process_recommendations_data([run])[0]["vehicles_number"] == 1

    def test_city_set_size_falls_back_to_the_best_route_when_there_is_no_city_set(self):
        run = make_run("2026-01-01", best_route=["A", "B", "C", "D"])
        del run["city_set"]

        assert prepare_process_recommendations_data([run])[0]["city_set_size"] == 4


class TestGenerateProcessRecommendations:
    @pytest.fixture
    def llm(self):
        with patch.object(process_recommendations, "LLMClient") as llm_class:
            llm_class.return_value = MagicMock()
            llm_class.return_value.generate_response.return_value = "recomendações"
            yield llm_class.return_value

    def test_raises_without_runs(self, llm):
        with pytest.raises(ValueError):
            generate_process_recommendations([])

        llm.generate_response.assert_not_called()

    def test_returns_the_text_generated_by_the_llm(self, llm):
        assert generate_process_recommendations([make_run("2026-01-01")]) == (
            "recomendações"
        )

    def test_prompt_carries_the_prepared_data_as_json(self, llm):
        runs = [make_run("2026-01-01"), make_run("2026-01-02")]

        generate_process_recommendations(runs)

        prompt = llm.generate_response.call_args.kwargs["prompt"]
        sent = json.loads(prompt[prompt.index("[") :])
        assert [item["date"] for item in sent] == ["2026-01-01", "2026-01-02"]

    def test_instructions_treat_different_vehicle_counts_as_distinct_contexts(
        self, llm
    ):
        generate_process_recommendations([make_run("2026-01-01")])

        instructions = llm.generate_response.call_args.kwargs["instructions"]
        assert "vehicles_number" in instructions
        assert "contextos distintos" in instructions
