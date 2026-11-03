from dataclasses import dataclass
from typing import List

from ...constants import PopulationType
from ..common import CityEntity, Matrix


@dataclass
class InitialPopulationArgs:
    population_strategy: PopulationType
    distances_matrix: Matrix
    population_size: int
    cities: List[CityEntity]
    origin_city_name: str | None = None
    vehicles_number: int = 1


@dataclass
class GenerateRandomArgs:
    population_size: int
    cities: List[CityEntity]
    origin_city_name: str | None = None
    vehicles_number: int = 1


@dataclass
class GenerateNearestNeighborArgs:
    distances_matrix: Matrix
    population_size: int
    cities: List[CityEntity]
    origin_city_name: str | None = None
    vehicles_number: int = 1


@dataclass
class GenerateCheapestInsertionArgs:
    distances_matrix: Matrix
    population_size: int
    cities: List[CityEntity]
    origin_city_name: str | None = None
    vehicles_number: int = 1
