import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from backend.app.history import filter_runs_by_period
from backend.llm import route_reports
from backend.llm.report_metrics import calculate_runs_metrics
from backend.llm.route_reports import (
    build_comparative_report_payload,
    generate_comparative_report,
)


def make_run(distance, duration, created_at="2026-01-01T00:00:00+00:00", vehicles=2):
    return {
        "id": f"{distance}-{duration}",
        "created_at": created_at,
        "population_type": "random",
        "population_size": 100,
        "mutation_probability": 0.5,
        "generations_run": 10,
        "best_distance": distance,
        "total_duration": duration,
        "stops_count": 5,
        "vehicles_number": vehicles,
    }


class TestCalculateRunsMetrics:
    @pytest.fixture
    def metrics(self):
        runs = [make_run(100.0, 3600), make_run(200.0, 7200), make_run(300.0, 10800)]
        return calculate_runs_metrics(runs)

    def test_distance_best_worst_and_average(self, metrics):
        assert metrics["runs_count"] == 3
        assert metrics["distance_km"]["best"] == 100.0
        assert metrics["distance_km"]["worst"] == 300.0
        assert metrics["distance_km"]["average"] == 200.0

    def test_distance_savings(self, metrics):
        assert metrics["distance_km"]["savings_vs_worst_km"] == 200.0
        assert metrics["distance_km"]["savings_vs_worst_percent"] == 66.7
        assert metrics["distance_km"]["savings_vs_average_percent"] == 50.0

    def test_duration_in_hours_and_minutes(self, metrics):
        assert metrics["duration"]["best"] == (1, 0)
        assert metrics["duration"]["worst"] == (3, 0)
        assert metrics["duration"]["average"] == (2, 0)
        assert metrics["duration"]["savings_vs_worst"] == (2, 0)
        assert metrics["duration"]["savings_vs_worst_percent"] == 66.7
        assert metrics["duration"]["savings_vs_average_percent"] == 50.0

    def test_single_run_has_no_savings(self):
        metrics = calculate_runs_metrics([make_run(100.0, 3600)])

        assert metrics["distance_km"]["savings_vs_worst_km"] == 0.0
        assert metrics["distance_km"]["savings_vs_worst_percent"] == 0.0
        assert metrics["duration"]["savings_vs_worst"] == (0, 0)


class TestComparativeReportPayload:
    def test_has_period_vehicles_metrics_and_runs(self):
        runs = [make_run(100.0, 3600), make_run(200.0, 7200)]

        payload = build_comparative_report_payload(runs, "week")

        assert payload["period"] == "últimos 7 dias"
        assert payload["vehicles_number"] == 2
        assert payload["metrics"]["runs_count"] == 2
        assert len(payload["runs"]) == 2

    def test_legacy_runs_without_vehicles_number_count_as_one_vehicle(self):
        run = make_run(100.0, 3600)
        del run["vehicles_number"]

        assert build_comparative_report_payload([run])["vehicles_number"] == 1

    def test_unknown_period_falls_back_to_the_whole_history(self):
        payload = build_comparative_report_payload([make_run(1.0, 60)], "xyz")

        assert payload["period"] == "todo o histórico"


class TestGenerateComparativeReport:
    @pytest.fixture
    def llm(self):
        with patch.object(route_reports, "LLMClient") as llm_class:
            llm_class.return_value = MagicMock()
            llm_class.return_value.generate_response.return_value = "relatório"
            yield llm_class.return_value

    def test_raises_without_runs(self, llm):
        with pytest.raises(ValueError):
            generate_comparative_report([])

    def test_sends_the_precomputed_metrics_to_the_llm(self, llm):
        runs = [make_run(100.0, 3600), make_run(200.0, 7200)]

        assert generate_comparative_report(runs, "day") == "relatório"

        kwargs = llm.generate_response.call_args.kwargs
        sent = json.loads(kwargs["prompt"][kwargs["prompt"].index("{") :])
        assert sent["period"] == "últimas 24 horas"
        assert sent["metrics"]["distance_km"]["savings_vs_worst_percent"] == 50.0

    def test_instructions_forbid_calculating_and_mention_vehicles(self, llm):
        generate_comparative_report([make_run(1.0, 60)])

        instructions = llm.generate_response.call_args.kwargs["instructions"]
        assert "NUNCA calcule" in instructions
        assert "metrics" in instructions
        assert "vehicles_number" in instructions


class TestFilterRunsByPeriod:
    NOW = datetime(2026, 1, 10, 12, tzinfo=timezone.utc)

    @pytest.fixture
    def runs(self):
        def at(delta):
            return make_run(1.0, 60, (self.NOW - delta).isoformat())

        return {
            "hour": at(timedelta(hours=1)),
            "three_days": at(timedelta(days=3)),
            "ten_days": at(timedelta(days=10)),
        }

    def test_all_keeps_every_run(self, runs):
        values = list(runs.values())
        assert filter_runs_by_period(values, "all", self.NOW) == values
        assert filter_runs_by_period(values, None, self.NOW) == values

    def test_day_keeps_only_the_last_24_hours(self, runs):
        result = filter_runs_by_period(list(runs.values()), "day", self.NOW)
        assert result == [runs["hour"]]

    def test_week_keeps_only_the_last_7_days(self, runs):
        result = filter_runs_by_period(list(runs.values()), "week", self.NOW)
        assert result == [runs["hour"], runs["three_days"]]

    def test_invalid_period_raises(self, runs):
        with pytest.raises(ValueError):
            filter_runs_by_period(list(runs.values()), "month", self.NOW)
