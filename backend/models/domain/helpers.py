from dataclasses import dataclass
from typing import List

from ..common import CityEntity, Matrix


@dataclass
class GetBestNNCityArgs:
    distances_matrix: Matrix
    cities: List[CityEntity]
    current_city: CityEntity
    possibilities_size: int = 4


@dataclass
class GenerateNNIndividualArgs:
    distances_matrix: Matrix
    cities: List[CityEntity]
    cities_per_vehicle: int
    remaining_cities_amount: int
    vehicles_number: int | None = 1
    origin: CityEntity | None = None
    possibilities_size: int = 4


@dataclass
class GenerateCIIndividualArgs:
    distances_matrix: Matrix
    cities: List[CityEntity]
    cities_per_vehicle: int
    remaining_cities_amount: int
    origin: CityEntity | None = None
    vehicles_number: int | None = 1
