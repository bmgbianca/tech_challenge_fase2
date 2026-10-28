from typing import List, Tuple, TypeAlias, TypedDict

Matrix: TypeAlias = dict[Tuple[int, int], float]
CityEntity: TypeAlias = dict[str, int | str | List[str] | Tuple[int, int] | bool]
Individual: TypeAlias = List[CityEntity]
PopulationFitness: TypeAlias = List[dict[str, Individual | float]]


class OptimizeRoutePayload(TypedDict):
    """Shape of the JSON body expected by POST /api/optimized-route, as
    sent by the frontend's optimizeRoute() (see frontend/src/api.js). All
    fields are required — see REQUIRED_OPTIMIZE_ROUTE_FIELDS in
    backend/app/routes.py for the runtime check."""

    population_type: str
    population_size: int
    mutation_probability: float
    origin_city: CityEntity
    destination_cities: List[CityEntity]
