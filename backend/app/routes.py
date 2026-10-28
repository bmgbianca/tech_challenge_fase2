from flask import Blueprint, jsonify, request

from ..config import OptimizeRoutePayload
from ..data import sao_paulo_cities
from ..ga import calculate_routes
from ..llm import (
    generate_comparative_report,
    generate_process_recommendations,
    prepare_route_data,
)
from ..services import geocode_cities, get_sp_municipalities
from .history import get_route_runs, save_route_run
from .report_cache import build_cache_key, get_cached_report, save_report
from .services import get_optimized_route

routes = Blueprint("routes", __name__)

CITIES_BY_NAME = {city["name"]: city for city in sao_paulo_cities}

REQUIRED_OPTIMIZE_ROUTE_FIELDS = (
    "population_type",
    "population_size",
    "mutation_probability",
    "origin_city",
    "destination_cities",
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
    query = request.args.get("q", "").strip().lower()

    if len(query) < 2:
        return jsonify([])

    municipalities = get_sp_municipalities()
    matches = [city for city in municipalities if query in city["name"].lower()]
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
    origin_city = payload["origin_city"]
    destination_cities = payload["destination_cities"]

    cities = destination_cities + [origin_city]

    try:
        result = get_optimized_route(
            fixed_start_city_name=origin_city["name"],
            population_type=population_type,
            population_size=population_size,
            mutation_probability=mutation_probability,
            cities=cities,
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    best_solution = result["best_solution"]
    best_route = [city["name"] for city in best_solution["individual"]]

    save_route_run(
        population_type=population_type,
        population_size=population_size,
        mutation_probability=mutation_probability,
        best_distance=best_solution["total_distance"],
        total_duration=result["total_duration"],
        critical_duration=best_solution["critical_duration"],
        stops_count=len(best_solution["individual"]),
        best_route=best_route,
        generations_run=len(result["fitness_history"]),
    )

    response = {
        "cities": sao_paulo_cities,
        "fitness_history": result["fitness_history"],
        "snapshots": result["snapshots"],
        "best_distance": best_solution["total_distance"],
        "critical_duration": best_solution["critical_duration"],
        "total_duration": result["total_duration"],
        "stops_count": len(best_solution["individual"]),
        "best_route": best_route,
    }

    return jsonify(response)


@routes.get("/api/route-runs")
def route_runs():
    return jsonify(get_route_runs())


@routes.post("/api/route-runs/comparative-report")
def comparative_report():
    payload = request.get_json(silent=True) or {}
    city_set = payload.get("city_set")

    if not city_set:
        return jsonify({"error": "O campo 'city_set' é obrigatório."}), 400

    target_city_set = sorted(city_set)
    matching_runs = [
        run
        for run in get_route_runs()
        if sorted(run.get("city_set", run["best_route"])) == target_city_set
    ]

    if not matching_runs:
        return (
            jsonify(
                {"error": "Nenhuma execução encontrada para esse conjunto de cidades."}
            ),
            404,
        )

    cache_key = build_cache_key(run["id"] for run in matching_runs)
    cached = get_cached_report(cache_key)

    if cached:
        return jsonify({"report": cached["report"], "cached": True})

    try:
        report = generate_comparative_report(matching_runs)
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
    payload = request.get_json(silent=True) or {}
    route_names = payload.get("route")

    if not route_names:
        return jsonify({"error": "O campo 'route' é obrigatório."}), 400

    try:
        route_cities = [CITIES_BY_NAME[name] for name in route_names]
    except KeyError as error:
        return jsonify({"error": f"Cidade desconhecida: {error}"}), 400

    calculated_routes = calculate_routes(sao_paulo_cities)
    best_solution = {"individual": route_cities}

    try:
        instructions = prepare_route_data(calculated_routes, best_solution)
    except Exception as error:
        return jsonify({"error": str(error)}), 500

    return jsonify({"driver_instructions": instructions})
