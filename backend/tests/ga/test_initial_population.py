import pytest

from backend.ga.initial_population import (
    generate_cheapest_insertion_individual,
    generate_nearest_neighbor_individual,
    generate_random_population,
    generate_start_city,
)


def make_city(name, location):
    return {"name": name, "id": location, "priority": False}


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
    matrix = {}
    for city_a in cities:
        for city_b in cities:
            if city_a is city_b:
                continue
            loc_a = city_a["id"]
            loc_b = city_b["id"]
            matrix[(loc_a, loc_b)] = abs(loc_a[0] - loc_b[0])
    return matrix


class TestGenerateRandomPopulation:
    def test_population_has_requested_size(self, cities):
        population = generate_random_population(5, cities)
        assert len(population) == 5

    def test_every_individual_contains_all_cities_once(self, cities):
        population = generate_random_population(5, cities)
        for individual in population:
            assert sorted(individual, key=id) == sorted(cities, key=id)

    def test_fixed_start_city_is_always_first(self, cities):
        population = generate_random_population(5, cities, fixed_start_city_name="C")
        for individual in population:
            assert individual[0]["name"] == "C"


class TestGenerateStartCity:
    def test_returns_requested_city(self, cities):
        start_city = generate_start_city(cities, fixed_start_city_name="B")
        assert start_city["name"] == "B"

    def test_raises_when_city_not_found(self, cities):
        with pytest.raises(ValueError):
            generate_start_city(cities, fixed_start_city_name="Nonexistent")

    def test_returns_a_city_from_the_list_when_no_fixed_start(self, cities):
        start_city = generate_start_city(cities)
        assert start_city in cities


class TestGenerateNearestNeighborIndividual:
    def test_visits_every_city_exactly_once(self, cities, distances_matrix):
        individual = generate_nearest_neighbor_individual(
            distances_matrix, cities, start_city=cities[0]
        )
        assert sorted(individual, key=id) == sorted(cities, key=id)

    def test_starts_at_given_city(self, cities, distances_matrix):
        individual = generate_nearest_neighbor_individual(
            distances_matrix, cities, start_city=cities[2]
        )
        assert individual[0] is cities[2]


class TestGenerateCheapestInsertionIndividual:
    def test_visits_every_city_exactly_once(self, cities, distances_matrix):
        individual = generate_cheapest_insertion_individual(
            distances_matrix, cities, fixed_start_city_name="A"
        )
        assert sorted(individual, key=id) == sorted(cities, key=id)

    def test_starts_at_fixed_city(self, cities, distances_matrix):
        individual = generate_cheapest_insertion_individual(
            distances_matrix, cities, fixed_start_city_name="D"
        )
        assert individual[0]["name"] == "D"
