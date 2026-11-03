from flask import Blueprint, jsonify, request

from ..models import GetOptimizedRouteArgs, OptimizeRoutePayload
from ..data import sao_paulo_cities
from ..helpers import normalize_text
from ..ga import calculate_routes
from ..llm import (
    generate_comparative_report,
    generate_process_recommendations,
    prepare_route_data,
)
from ..services import geocode_cities, get_sp_municipalities
from .history import filter_runs_by_period, get_route_runs, save_route_run
from .report_cache import build_cache_key, get_cached_report, save_report
from .services import get_optimized_route, get_routes_names

routes = Blueprint("routes", __name__)

REQUIRED_OPTIMIZE_ROUTE_FIELDS = (
    "population_type",
    "population_size",
    "mutation_probability",
    "destination_cities",
    "vehicles_number",
)


def validate_optimize_route_payload(payload: dict) -> OptimizeRoutePayload:
    """Ensures the request body has every field required by
    OptimizeRoutePayload. Raises ValueError (caught by the route handler
    and turned into a 400) naming every missing field at once."""

    missing_fields = [
        field for field in REQUIRED_OPTIMIZE_ROUTE_FIELDS if field not in payload
    ]

    if missing_fields:
        raise ValueError(
            "Campos obrigatórios ausentes no payload: " + ", ".join(missing_fields)
        )

    return payload


@routes.get("/api/cities")
def get_cities():
    return jsonify(sao_paulo_cities)


@routes.get("/api/cities/search")
def search_cities():
    query = normalize_text(request.args.get("q", "").strip())

    if len(query) < 2:
        return jsonify([])

    municipalities = get_sp_municipalities()
    matches = [
        city for city in municipalities if query in normalize_text(city["name"])
    ]
    return jsonify(matches)


@routes.post("/api/geocode-cities")
def geocode_cities_route():
    payload = request.get_json(silent=True) or {}
    names = payload.get("cities")

    if not names:
        return jsonify({"error": "O campo 'cities' é obrigatório."}), 400

    try:
        coordinates_by_name = geocode_cities(names)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": str(error)}), 500

    return jsonify({"coordinates": coordinates_by_name})


@routes.post("/api/optimized-route")
def optimize():
    payload = request.get_json(silent=True) or {}

    try:
        payload: OptimizeRoutePayload = validate_optimize_route_payload(payload)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    population_type = payload["population_type"]
    population_size = int(payload["population_size"])
    mutation_probability = float(payload["mutation_probability"])
    origin_city = payload.get("origin_city") or None
    destination_cities = payload["destination_cities"]
    vehicles_number = int(payload["vehicles_number"])

    cities = destination_cities + [origin_city] if origin_city else destination_cities

    try:
        result = get_optimized_route(
            GetOptimizedRouteArgs(
                origin_city=origin_city["name"] if origin_city else None,
                population_type=population_type,
                population_size=population_size,
                mutation_probability=mutation_probability,
                cities=cities,
                vehicles_number=vehicles_number,
            )
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    best_solution = result["best_solution"]

    """One list of city names per vehicle, e.g. [["A", "B"], ["A", "C"]].
    The origin appears once in every vehicle route, so stops_count counts
    the distinct cities of the solution:"""
    best_route = get_routes_names(best_solution["individual"])
    stops_count = len({name for vehicle in best_route for name in vehicle})

    save_route_run(
        population_type=population_type,
        population_size=population_size,
        mutation_probability=mutation_probability,
        best_distance=best_solution["total_distance"],
        total_duration=result["total_duration"],
        priorities_on_time=best_solution["priorities_on_time"],
        stops_count=stops_count,
        vehicles_number=vehicles_number,
        best_route=best_route,
        generations_run=len(result["fitness_history"]),
    )

    response = {
        "cities": cities,
        "fitness_history": result["fitness_history"],
        "snapshots": result["snapshots"],
        "best_distance": best_solution["total_distance"],
        "priorities_on_time": best_solution["priorities_on_time"],
        "total_duration": result["total_duration"],
        "stops_count": stops_count,
        "vehicles_number": vehicles_number,
        "best_route": best_route,
    }

    return jsonify(response)


@routes.get("/api/route-runs")
def route_runs():
    return jsonify(get_route_runs())


@routes.post("/api/route-runs/comparative-report")
def comparative_report():
    """Comparative report for the runs of one city set and one vehicles
    number, optionally restricted to a period ("day", "week" or "all")."""
    payload = request.get_json(silent=True) or {}
    city_set = payload.get("city_set")
    vehicles_number = payload.get("vehicles_number")
    period = payload.get("period") or "all"

    if not city_set:
        return jsonify({"error": "O campo 'city_set' é obrigatório."}), 400

    try:
        period_runs = filter_runs_by_period(get_route_runs(), period)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    target_city_set = sorted(city_set)
    matching_runs = [
        run
        for run in period_runs
        if sorted(run.get("city_set", run["best_route"])) == target_city_set
        and (
            vehicles_number is None
            or run.get("vehicles_number", 1) == vehicles_number
        )
    ]

    if not matching_runs:
        return (
            jsonify(
                {
                    "error": "Nenhuma execução encontrada para esse conjunto de "
                    "cidades, número de veículos e período."
                }
            ),
            404,
        )

    cache_key = f"{period}:" + build_cache_key(run["id"] for run in matching_runs)
    cached = get_cached_report(cache_key)

    if cached:
        return jsonify({"report": cached["report"], "cached": True})

    try:
        report = generate_comparative_report(matching_runs, period)
    except Exception as error:
        return jsonify({"error": str(error)}), 500

    save_report(cache_key, report, [run["id"] for run in matching_runs])

    return jsonify({"report": report, "cached": False})


@routes.post("/api/process-recommendations")
def process_recommendations():
    all_runs = get_route_runs()

    if not all_runs:
        return (
            jsonify({"error": "Nenhuma execução encontrada no histórico."}),
            404,
        )

    cache_key = "global:" + build_cache_key(run["id"] for run in all_runs)
    cached = get_cached_report(cache_key)

    if cached:
        return jsonify({"report": cached["report"], "cached": True})

    try:
        report = generate_process_recommendations(all_runs)
    except Exception as error:
        return jsonify({"error": str(error)}), 500

    save_report(cache_key, report, [run["id"] for run in all_runs])

    return jsonify({"report": report, "cached": False})


@routes.post("/api/driver-instructions")
def driver_instructions():
    """Builds the driver instructions for a route the frontend already has.
    The cities (with coordinates) come in the request, since they are the
    ones the user chose for that run, not a fixed dataset."""
    payload = request.get_json(silent=True) or {}
    route_names = payload.get("route")
    cities = payload.get("cities")

    if not route_names:
        return jsonify({"error": "O campo 'route' é obrigatório."}), 400

    if not cities:
        return jsonify({"error": "O campo 'cities' é obrigatório."}), 400

    """'route' is one list of city names per vehicle. A flat list of names
    is also accepted and treated as a single vehicle:"""
    vehicles_names = route_names if isinstance(route_names[0], list) else [route_names]

    cities_by_name = {city["name"]: city for city in cities}

    try:
        individual = [
            [cities_by_name[name] for name in vehicle] for vehicle in vehicles_names
        ]
    except KeyError as error:
        return (
            jsonify({"error": f"Cidade da rota ausente em 'cities': {error}"}),
            400,
        )

    # The matrices only need the cities that are actually in the route:
    route_cities = list({id(city): city for vehicle in individual for city in vehicle}.values())

    try:
        calculated_routes = calculate_routes(route_cities)
        instructions = prepare_route_data(calculated_routes, {"individual": individual})
    except Exception as error:
        return jsonify({"error": str(error)}), 500

    return jsonify({"driver_instructions": instructions})
