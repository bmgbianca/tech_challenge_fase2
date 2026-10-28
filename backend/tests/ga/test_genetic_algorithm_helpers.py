import pytest

from backend.config.constants import TIME_LIMIT
from backend.ga.calculation import (
    calculate_critical_duration,
    calculate_fitness,
    calculate_solution_duration,
    get_distance,
)
from backend.ga.crossover import order_crossover
from backend.ga.mutation import segment_shuffle_mutation
from backend.ga.selection import is_solution_valid, sort_population_by_fitness


def make_city(name, location, priority=False):
    return {"name": name, "id": location, "priority": priority}


@pytest.fixture
def cities():
    return [
        make_city("A", (0, 0)),
        make_city("B", (1, 0)),
        make_city("C", (2, 0)),
        make_city("D", (3, 0)),
    ]


@pytest.fixture
def distances_matrix(cities):
    # distance between consecutive cities is 10, used both ways
    matrix = {}
    for i in range(len(cities) - 1):
        loc_a = cities[i]["id"]
        loc_b = cities[i + 1]["id"]
        matrix[(loc_a, loc_b)] = 10.0
        matrix[(loc_b, loc_a)] = 10.0
    return matrix


class TestCalculateFitness:
    def test_sums_distance_along_route(self, cities, distances_matrix):
        assert calculate_fitness(distances_matrix, cities) == 30.0

    def test_single_city_route_has_zero_distance(self, cities, distances_matrix):
        assert calculate_fitness(distances_matrix, cities[:1]) == 0.0


class TestGetDistance:
    def test_returns_known_distance(self, cities, distances_matrix):
        loc_a = cities[0]["id"]
        loc_b = cities[1]["id"]
        assert get_distance(distances_matrix, loc_a, loc_b) == 10.0

    def test_returns_zero_for_unknown_pair(self, distances_matrix):
        assert get_distance(distances_matrix, (99, 99), (100, 100)) == 0.0


class TestCalculateCriticalDuration:
    def test_returns_zero_when_no_priority_city(self, cities, distances_matrix):
        assert calculate_critical_duration(distances_matrix, cities) == 0

    def test_counts_only_up_to_last_priority_city(self, cities, distances_matrix):
        cities[2]["priority"] = True  # city C, index 2
        duration = calculate_critical_duration(distances_matrix, cities)
        # route A->B->C = 10 + 10 = 20, ignoring the trailing D leg
        assert duration == 20.0


class TestCalculateSolutionDuration:
    def test_sums_duration_for_full_route(self, cities, distances_matrix):
        assert calculate_solution_duration(distances_matrix, cities) == 30.0


class TestIsSolutionValid:
    def test_valid_when_no_priority_city(self, cities, distances_matrix):
        assert is_solution_valid(distances_matrix, cities) is True

    def test_valid_when_priority_city_within_time_limit(self, cities, distances_matrix):
        cities[1]["priority"] = True
        assert is_solution_valid(distances_matrix, cities) is True

    def test_invalid_when_priority_city_exceeds_time_limit(self, cities):
        slow_matrix = {
            (cities[0]["id"], cities[1]["id"]): TIME_LIMIT + 1,
        }
        cities[1]["priority"] = True
        assert is_solution_valid(slow_matrix, cities) is False


class TestOrderCrossover:
    def test_children_contain_same_cities_as_parents(self, cities):
        parent1 = cities
        parent2 = list(reversed(cities))

        child1, child2 = order_crossover([parent1, parent2])

        assert sorted(child1, key=id) == sorted(parent1, key=id)
        assert sorted(child2, key=id) == sorted(parent1, key=id)
        assert None not in child1
        assert None not in child2


class TestSegmentShuffleMutation:
    def test_keeps_same_set_of_cities(self, cities):
        mutated = segment_shuffle_mutation(list(cities), mutation_probability=1.0)
        assert sorted(mutated, key=id) == sorted(cities, key=id)

    def test_never_mutates_fixed_first_city(self, cities):
        mutated = segment_shuffle_mutation(
            list(cities), mutation_probability=1.0, fixed_first_index=True
        )
        assert mutated[0] is cities[0]

    def test_no_mutation_when_probability_is_zero(self, cities):
        mutated = segment_shuffle_mutation(list(cities), mutation_probability=0.0)
        assert mutated == cities


class TestSortPopulationByFitness:
    def test_orders_valid_solutions_by_distance(self, cities, distances_matrix):
        population_fitness = [
            {"individual": cities, "total_distance": 30.0},
            {"individual": cities[:3], "total_distance": 20.0},
        ]
        sorted_population = sort_population_by_fitness(
            distances_matrix, population_fitness
        )
        assert sorted_population[0]["total_distance"] == 20.0
