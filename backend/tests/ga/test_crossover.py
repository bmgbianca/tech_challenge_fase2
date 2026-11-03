import copy
from unittest.mock import patch

import pytest

from backend.ga import order_crossover


def make_city(name, city_id):
    return {"name": name, "id": city_id, "priority": False}


def crossover(parents, is_origin=True):
    return order_crossover({"parents": parents, "is_origin": is_origin})


def route_names(individual):
    return [[city["name"] for city in route] for route in individual]


@pytest.fixture
def cities():
    return {name: make_city(name, index) for index, name in enumerate("ABCDEFG")}


@pytest.fixture
def parents(cities):
    a, b, c, d, e, f, g = (cities[name] for name in "ABCDEFG")
    return [
        [[a, b, c, d], [a, e, f, g]],
        [[a, g, f, e], [a, d, c, b]],
    ]


@pytest.fixture
def parents_without_origin(cities):
    a, b, c, d, e, f, g = (cities[name] for name in "ABCDEFG")
    # uneven vehicles (3 + 2 + 2 cities), no city shared between routes
    return [
        [[a, b, c], [d, e], [f, g]],
        [[g, f, e], [d, c], [b, a]],
    ]


class TestOrderCrossoverWithOrigin:
    def test_children_visit_every_city_exactly_once(self, parents):
        for _ in range(100):
            for child in crossover(parents):
                visited = [city["name"] for route in child for city in route[1:]]
                assert sorted(visited) == list("BCDEFG")

    def test_origin_starts_every_route_of_the_children(self, parents):
        for _ in range(100):
            for child in crossover(parents):
                assert all(route[0]["name"] == "A" for route in child)

    def test_children_keep_the_number_of_cities_per_vehicle(self, cities):
        a, b, c, d, e, f, g = (cities[name] for name in "ABCDEFG")
        # uneven vehicles: 3 + 2 + 1 clients
        parent1 = [[a, b, c, d], [a, e, f], [a, g]]
        parent2 = [[a, g, f, e], [a, d, c], [a, b]]

        for _ in range(100):
            child1, child2 = crossover([parent1, parent2])
            assert [len(route) for route in child1] == [4, 3, 2]
            assert [len(route) for route in child2] == [4, 3, 2]

    def test_does_not_change_the_parents(self, parents):
        parents_before = copy.deepcopy(parents)

        for _ in range(100):
            crossover(parents)

        assert parents == parents_before

    def test_single_vehicle_individuals(self, cities):
        a, b, c, d = (cities[name] for name in "ABCD")
        child1, child2 = crossover([[[a, b, c, d]], [[a, d, c, b]]])

        for child in (child1, child2):
            assert len(child) == 1
            assert child[0][0]["name"] == "A"
            assert sorted(city["name"] for city in child[0]) == list("ABCD")

    def test_builds_the_children_from_the_segment_and_the_other_parent_order(
        self, parents
    ):
        # full routes: parent1 = A B C D E F G, parent2 = A G F E D C B
        # segment [1:3] is kept from each parent and the rest is filled with
        # the missing cities in the order of the other parent
        with patch("backend.ga.crossover.random.randrange", return_value=1), patch(
            "backend.ga.crossover.random.randint", return_value=3
        ):
            child1, child2 = crossover(parents)

        # child1 = A B C G F E D, child2 = A G F B C D E
        assert route_names(child1) == [["A", "B", "C", "G"], ["A", "F", "E", "D"]]
        assert route_names(child2) == [["A", "G", "F", "B"], ["A", "C", "D", "E"]]


class TestOrderCrossoverWithoutOrigin:
    def test_children_visit_every_city_exactly_once(self, parents_without_origin):
        for _ in range(100):
            for child in crossover(parents_without_origin, is_origin=False):
                visited = [city["name"] for route in child for city in route]
                assert sorted(visited) == list("ABCDEFG")

    def test_children_keep_the_number_of_cities_per_vehicle(
        self, parents_without_origin
    ):
        for _ in range(100):
            child1, child2 = crossover(parents_without_origin, is_origin=False)
            assert [len(route) for route in child1] == [3, 2, 2]
            assert [len(route) for route in child2] == [3, 2, 2]

    def test_does_not_change_the_parents(self, parents_without_origin):
        parents_before = copy.deepcopy(parents_without_origin)

        for _ in range(100):
            crossover(parents_without_origin, is_origin=False)

        assert parents_without_origin == parents_before

    def test_builds_the_children_from_the_segment_and_the_other_parent_order(
        self, parents_without_origin
    ):
        # full routes: parent1 = A B C D E F G, parent2 = G F E D C B A
        # segment [2:5] is kept from each parent
        with patch("backend.ga.crossover.random.randrange", return_value=2), patch(
            "backend.ga.crossover.random.randint", return_value=5
        ):
            child1, child2 = crossover(parents_without_origin, is_origin=False)

        # child1 = G F C D E B A, child2 = A B E D C F G
        assert route_names(child1) == [["G", "F", "C"], ["D", "E"], ["B", "A"]]
        assert route_names(child2) == [["A", "B", "E"], ["D", "C"], ["F", "G"]]
