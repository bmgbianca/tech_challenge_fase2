import pytest

from backend.constants import TIME_LIMIT
from backend.ga import (
    is_solution_valid as _is_solution_valid,
    select_best_invalid_solution as _select_best_invalid_solution,
    select_winner_solution as _select_winner_solution,
    sort_population_by_fitness as _sort_population_by_fitness,
)
from backend.models import (
    IsSolutionValidArgs,
    SelectBestInvalidSolutionArgs,
    SelectWinnerSolutionArgs,
    SortPopulationByFitnessArgs,
)


def is_solution_valid(duration_matrix, solution):
    return _is_solution_valid(
        IsSolutionValidArgs(duration_matrix=duration_matrix, solution=solution)
    )


def select_best_invalid_solution(duration_matrix, solutions):
    return _select_best_invalid_solution(
        SelectBestInvalidSolutionArgs(
            duration_matrix=duration_matrix, solutions=solutions
        )
    )


def select_winner_solution(duration_matrix, solutions):
    return _select_winner_solution(
        SelectWinnerSolutionArgs(duration_matrix=duration_matrix, solutions=solutions)
    )


def sort_population_by_fitness(duration_matrix, population_fitness):
    return _sort_population_by_fitness(
        SortPopulationByFitnessArgs(
            duration_matrix=duration_matrix, population_fitness=population_fitness
        )
    )


LATE_BY_100 = TIME_LIMIT + 100
LATE_BY_5000 = TIME_LIMIT + 5000


def make_city(name, city_id, priority=False):
    return {"name": name, "id": city_id, "priority": priority}


def make_solution(individual, total_distance):
    return {"individual": individual, "total_distance": total_distance}


@pytest.fixture
def cities():
    # B and C are priority cities
    return [
        make_city("A", 0),
        make_city("B", 1, priority=True),
        make_city("C", 2, priority=True),
        make_city("D", 3),
    ]


@pytest.fixture
def durations():
    """Cities lie on a line, 10 seconds apart, except for two legs that make
    a vehicle arrive late: A->B (100 s over TIME_LIMIT) and A->C (5000 s over)."""
    matrix = {
        (a, b): 10.0 * abs(a - b) for a in range(4) for b in range(4) if a != b
    }
    matrix[(0, 1)] = matrix[(1, 0)] = LATE_BY_100
    matrix[(0, 2)] = matrix[(2, 0)] = LATE_BY_5000
    return matrix


@pytest.fixture
def on_time_durations():
    return {(a, b): 10.0 * abs(a - b) for a in range(4) for b in range(4) if a != b}


class TestIsSolutionValid:
    def test_valid_when_there_is_no_priority_city(self, on_time_durations):
        a, d = make_city("A", 0), make_city("D", 3)
        assert is_solution_valid(on_time_durations, [[a, d], [a, d]]) is True

    def test_valid_when_every_priority_city_is_on_time(self, cities, on_time_durations):
        a, b, c, d = cities
        assert is_solution_valid(on_time_durations, [[a, b], [a, d, c]]) is True

    def test_invalid_when_one_vehicle_reaches_a_priority_city_too_late(
        self, cities, durations
    ):
        a, b, c, d = cities
        # first vehicle is fine (A->D->C), second reaches B too late
        assert is_solution_valid(durations, [[a, d, c], [a, b]]) is False

    def test_ignores_the_route_after_the_last_priority_city(
        self, cities, on_time_durations
    ):
        a, b, c, d = cities
        late_after_b = {**on_time_durations, (1, 3): TIME_LIMIT * 2}
        assert is_solution_valid(late_after_b, [[a, b, d]]) is True

    def test_slow_vehicle_without_priority_city_is_still_valid(self, cities):
        a, b, _, d = cities
        durations = {(0, 1): 10.0, (0, 3): TIME_LIMIT * 2}
        assert is_solution_valid(durations, [[a, b], [a, d]]) is True


class TestSelectBestInvalidSolution:
    def test_prefers_the_solution_with_fewer_unmet_priorities(self, cities, durations):
        a, b, c, d = cities
        # both vehicles late: B (A->B) and C (A->C)
        two_unmet = make_solution([[a, b], [a, c]], total_distance=1)
        # only B is late, C is reached on time through D
        one_unmet = make_solution([[a, b], [a, d, c]], total_distance=99)

        assert select_best_invalid_solution(durations, [two_unmet, one_unmet]) is one_unmet
        assert select_best_invalid_solution(durations, [one_unmet, two_unmet]) is one_unmet

    def test_counts_unmet_priorities_in_every_vehicle(self, cities, durations):
        a, b, c, d = cities
        one_vehicle_late = make_solution([[a, d, c], [a, b]], total_distance=50)
        two_vehicles_late = make_solution([[a, b], [a, c]], total_distance=10)

        best = select_best_invalid_solution(
            durations, [two_vehicles_late, one_vehicle_late]
        )
        assert best is one_vehicle_late

    def test_same_unmet_count_prefers_the_smaller_delay(self, cities, durations):
        a, b, c, _ = cities
        late_by_100 = make_solution([[a, b]], total_distance=99)  # one unmet, 100 s
        late_by_5000 = make_solution([[a, c]], total_distance=1)  # one unmet, 5000 s

        assert select_best_invalid_solution(durations, [late_by_5000, late_by_100]) is late_by_100
        assert select_best_invalid_solution(durations, [late_by_100, late_by_5000]) is late_by_100

    def test_same_delay_prefers_the_smaller_distance(self, cities, durations):
        a, b, _, _ = cities
        shorter = make_solution([[a, b]], total_distance=10)
        longer = make_solution([[a, b]], total_distance=20)

        assert select_best_invalid_solution(durations, [longer, shorter]) is shorter
        assert select_best_invalid_solution(durations, [shorter, longer]) is shorter


class TestSelectWinnerSolution:
    def test_both_valid_picks_the_smaller_distance(self, cities, on_time_durations):
        a, b, c, d = cities
        short = make_solution([[a, b, c, d]], total_distance=30)
        long = make_solution([[a, d, c, b]], total_distance=50)

        assert select_winner_solution(on_time_durations, [long, short]) is short

    def test_valid_solution_beats_invalid_one_even_with_larger_distance(
        self, cities, durations
    ):
        a, b, c, d = cities
        valid = make_solution([[a, d, c], [a, d]], total_distance=500)
        invalid = make_solution([[a, b]], total_distance=1)

        assert select_winner_solution(durations, [invalid, valid]) is valid
        assert select_winner_solution(durations, [valid, invalid]) is valid

    def test_both_invalid_picks_the_one_with_fewer_unmet_priorities(
        self, cities, durations
    ):
        a, b, c, d = cities
        two_unmet = make_solution([[a, b], [a, c]], total_distance=1)
        one_unmet = make_solution([[a, b], [a, d, c]], total_distance=99)

        assert select_winner_solution(durations, [two_unmet, one_unmet]) is one_unmet


class TestSortPopulationByFitness:
    def test_orders_valid_solutions_by_distance(self, cities, on_time_durations):
        a, b, c, d = cities
        population = [
            make_solution([[a, d, c, b]], total_distance=50),
            make_solution([[a, b, c, d]], total_distance=30),
            make_solution([[a, c, b, d]], total_distance=40),
        ]

        sorted_population = sort_population_by_fitness(on_time_durations, population)

        assert [s["total_distance"] for s in sorted_population] == [30, 40, 50]

    def test_valid_solutions_come_before_invalid_ones(self, cities, durations):
        a, b, c, d = cities
        invalid = make_solution([[a, b]], total_distance=1)
        valid = make_solution([[a, d, c]], total_distance=500)

        assert sort_population_by_fitness(durations, [invalid, valid]) == [
            valid,
            invalid,
        ]

    def test_invalid_solutions_are_ordered_by_unmet_priorities(
        self, cities, durations
    ):
        a, b, c, d = cities
        two_unmet = make_solution([[a, b], [a, c]], total_distance=1)
        one_unmet = make_solution([[a, b], [a, d, c]], total_distance=99)

        assert sort_population_by_fitness(durations, [two_unmet, one_unmet]) == [
            one_unmet,
            two_unmet,
        ]
