from operator import itemgetter
from typing import List, Tuple
import random

from ..models import (
    BuildChildRouteArgs,
    CityEntity,
    FlattenIndividualArgs,
    Individual,
    OrderCrossoverArgs,
    SplitIntoVehiclesArgs,
)

""" Perform order crossover (OX) between two parent individuals to
create two child individuals. Each individual is flattened into a single
sequence (origin only once), crossed, and split back into vehicles. """

"""Joins all vehicle routes into one sequence, keeping the origin only once at the start, and returns it with the size of each vehicle route."""


def flatten_individual(
    arg: FlattenIndividualArgs,
) -> Tuple[List[CityEntity], List[int]]:
    individual, is_origin = itemgetter("individual", "is_origin")(arg)
    full_route = individual[0][:]

    split_start_index = 1 if is_origin else 0
    for vehicle in individual[1:]:
        full_route += vehicle[split_start_index:]

    vehicles_sizes = [len(vehicle) for vehicle in individual]

    return full_route, vehicles_sizes


"""Copies the segment from one parent and fills the other positions
with the missing cities, in the order they appear in the other parent."""


def build_child_route(arg: BuildChildRouteArgs) -> List[CityEntity]:
    child_route = [None] * len(arg["segment_parent_route"])
    child_route[arg["start_index"] : arg["end_index"]] = arg["segment_parent_route"][
        arg["start_index"] : arg["end_index"]
    ]

    remaining_positions = [
        i
        for i in range(len(child_route))
        if i < arg["start_index"] or i >= arg["end_index"]
    ]
    remaining_genes = [
        gene for gene in arg["filler_parent_route"] if gene not in child_route
    ]

    for position, gene in zip(remaining_positions, remaining_genes):
        child_route[position] = gene

    return child_route


"""Splits the full route back into vehicle routes, placing the origin
(first city) at the start of every one of them."""


def split_into_vehicles(arg: SplitIntoVehiclesArgs) -> Individual:
    full_route, vehicles_sizes, is_origin = itemgetter(
        "full_route", "vehicles_sizes", "is_origin"
    )(arg)
    origin = full_route[0]
    remaining_cities = full_route[:]
    vehicles: Individual = []

    for index, size in enumerate(vehicles_sizes):
        range_end = size if index == 0 or not is_origin else size - 1
        route = remaining_cities[:range_end]
        vehicles.append(route if index == 0 or not is_origin else [origin] + route)
        del remaining_cities[:range_end]

    return vehicles


def order_crossover(arg: OrderCrossoverArgs) -> List[Individual]:
    parents, is_origin = itemgetter("parents", "is_origin")(arg)
    parent1_route, parent1_sizes = flatten_individual(
        {
            "individual": parents[0],
            "is_origin": is_origin,
        }
    )
    parent2_route, parent2_sizes = flatten_individual(
        {"individual": parents[1], "is_origin": is_origin}
    )

    cities_length = len(parent1_route)

    """Used cities_lenght - 1 to avoid the last city being selected
    as the start index."""
    start_index = random.randrange(0, cities_length - 1)

    """Used cities_lenght to allow the last city to be
    included in the range."""
    end_index = random.randint(start_index + 1, cities_length)

    child1_route = build_child_route(
        {
            "segment_parent_route": parent1_route,
            "filler_parent_route": parent2_route,
            "start_index": start_index,
            "end_index": end_index,
        }
    )
    child2_route = build_child_route(
        {
            "segment_parent_route": parent2_route,
            "filler_parent_route": parent1_route,
            "start_index": start_index,
            "end_index": end_index,
        }
    )

    return [
        split_into_vehicles(
            {
                "full_route": child1_route,
                "vehicles_sizes": parent1_sizes,
                "is_origin": is_origin,
            }
        ),
        split_into_vehicles(
            {
                "full_route": child2_route,
                "vehicles_sizes": parent2_sizes,
                "is_origin": is_origin,
            }
        ),
    ]
