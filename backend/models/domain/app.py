from dataclasses import dataclass, field
from typing import List, TypedDict

from ...constants import (
    MUTATION_PROBABILITY,
    POPULATION_SIZE,
    PLATEAU_WINDOW,
    MAX_GENERATIONS,
    PopulationType,
)
from ..common import CityEntity
from ...data import sao_paulo_cities


class OptimizeRoutePayload(TypedDict):
    """Shape of the JSON body expected by POST /api/optimized-route, as
    sent by the frontend's optimizeRoute(). All
    fields are required — see REQUIRED_OPTIMIZE_ROUTE_FIELDS in
    backend/app/routes.py for the runtime check."""

    origin_city: CityEntity | None
    destination_cities: List[CityEntity]
    population_type: PopulationType
    population_size: int
    mutation_probability: float
    vehicles_number: int


@dataclass
class GetOptimizedRouteArgs:
    origin_city: str | None
    population_type: PopulationType = "nearest_neighbor"
    population_size: int = POPULATION_SIZE
    mutation_probability: float = MUTATION_PROBABILITY
    max_generations: int = MAX_GENERATIONS
    plateau_window: int = PLATEAU_WINDOW
    vehicles_number: int | None = 1
    cities: List[CityEntity] | None = field(
        default_factory=lambda: list(sao_paulo_cities)
    )


@dataclass
class RunGeneticAlgorithmArgs:
    origin_city: str | None
    cities: List[CityEntity] = field(default_factory=lambda: list(sao_paulo_cities))
    population_type: PopulationType = "nearest_neighbor"
    population_size: int = POPULATION_SIZE
    mutation_probability: float = MUTATION_PROBABILITY
    max_generations: int = MAX_GENERATIONS
    plateau_window: int = PLATEAU_WINDOW
    vehicles_number: int | None = 1
    # Distances/durations already calculated (e.g. cached by the demo). When
    # None, they are requested to OpenRouteService:
    calculated_routes: dict | None = None
