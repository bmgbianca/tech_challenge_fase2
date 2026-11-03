from typing import List, TypedDict
from ..common import CityEntity, Individual


class OrderCrossoverArgs(TypedDict):
    parents: List[Individual]
    is_origin: bool | None


class FlattenIndividualArgs(TypedDict):
    individual: Individual
    is_origin: bool | None


class BuildChildRouteArgs(TypedDict):
    segment_parent_route: List[CityEntity]
    filler_parent_route: List[CityEntity]
    start_index: int
    end_index: int


class SplitIntoVehiclesArgs(TypedDict):
    full_route: List[CityEntity]
    vehicles_sizes: List[int]
    is_origin: bool | None
