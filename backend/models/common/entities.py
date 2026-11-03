from typing import List, Tuple, TypeAlias, TypedDict

Matrix: TypeAlias = dict[Tuple[int, int], float]


class CityEntity(TypedDict):
    name: str
    id: int
    coordinates: List[str]
    map_location: Tuple[int, int]
    priority: bool


Individual: TypeAlias = List[List[CityEntity]]


class IndividualWithFitness(TypedDict):
    individual: Individual
    total_distance: float
    priorities_on_time: bool


PopulationWithFitness: TypeAlias = List[IndividualWithFitness]
