import json
from pathlib import Path

import requests

IBGE_SP_MUNICIPALITIES_URL = (
    "https://servicodados.ibge.gov.br/api/v1/localidades/estados/SP/municipios"
)
IBGE_MALHA_URL = "https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{id}"

CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "sp_municipalities.json"
COORDINATES_CACHE_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "sp_municipality_coordinates.json"
)


def _fetch_from_ibge():
    response = requests.get(IBGE_SP_MUNICIPALITIES_URL, timeout=10)
    response.raise_for_status()

    municipalities = [
        {"id": item["id"], "name": item["nome"]} for item in response.json()
    ]
    municipalities.sort(key=lambda item: item["name"])
    return municipalities


def get_sp_municipalities():
    """Returns every municipality in the state of São Paulo (645, per IBGE),
    fetched once from the IBGE public API and cached locally — this is
    static reference data (names only, no coordinates), so there's no need
    to hit IBGE again once the cache file exists."""

    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    municipalities = _fetch_from_ibge()

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as file:
        json.dump(municipalities, file, ensure_ascii=False, indent=2)

    return municipalities


def _municipality_id_by_name(name):
    for municipality in get_sp_municipalities():
        if municipality["name"].lower() == name.lower():
            return municipality["id"]
    return None


def _polygon_points(geometry):
    """Flattens a GeoJSON Polygon or MultiPolygon's exterior ring(s) into a
    flat list of [lon, lat] points, for a simple centroid calculation."""

    rings = (
        geometry["coordinates"]
        if geometry["type"] == "Polygon"
        else [ring for polygon in geometry["coordinates"] for ring in polygon]
    )
    return [point for ring in rings for point in ring]


def _read_coordinates_cache():
    if not COORDINATES_CACHE_FILE.exists():
        return {}
    with open(COORDINATES_CACHE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def _write_coordinates_cache(cache):
    COORDINATES_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(COORDINATES_CACHE_FILE, "w", encoding="utf-8") as file:
        json.dump(cache, file, ensure_ascii=False, indent=2)


def _fetch_centroid(municipality_id):
    url = IBGE_MALHA_URL.format(id=municipality_id)
    response = requests.get(
        url, params={"formato": "application/vnd.geo+json"}, timeout=10
    )
    response.raise_for_status()

    geometry = response.json()["features"][0]["geometry"]
    points = _polygon_points(geometry)

    avg_lon = sum(point[0] for point in points) / len(points)
    avg_lat = sum(point[1] for point in points) / len(points)

    return [avg_lon, avg_lat]


def geocode_city(name):
    """Resolves a São Paulo municipality name to an approximate [lon, lat]
    coordinate, by averaging the points of its official boundary geometry
    (from IBGE's own "malhas" API) — no external geocoder involved, and no
    risk of hitting a third-party API's rate limit, since this only ever
    runs for the handful of cities a user actually selects, and the result
    is cached locally afterwards (a municipality's shape never changes)."""

    municipality_id = _municipality_id_by_name(name)
    if municipality_id is None:
        raise ValueError(f"Município não encontrado: {name}")

    cache = _read_coordinates_cache()
    cache_key = str(municipality_id)

    if cache_key in cache:
        return cache[cache_key]

    coordinates = _fetch_centroid(municipality_id)

    cache[cache_key] = coordinates
    _write_coordinates_cache(cache)

    return coordinates


def geocode_cities(names):
    return {name: geocode_city(name) for name in names}
