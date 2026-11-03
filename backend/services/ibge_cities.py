import json
from pathlib import Path

import requests

from .api_requests import openrouteservice_key

IBGE_SP_MUNICIPALITIES_URL = (
    "https://servicodados.ibge.gov.br/api/v1/localidades/estados/SP/municipios"
)
ORS_GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
# bounding box of the state of São Paulo, to avoid same-name towns elsewhere
SP_BOUNDING_BOX = {
    "boundary.rect.min_lon": -53.2,
    "boundary.rect.max_lon": -44.1,
    "boundary.rect.min_lat": -25.4,
    "boundary.rect.max_lat": -19.7,
}

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
    """Returns every municipality in the state of São Paulo (645, per IBGE).
    This is static reference data (names only, no coordinates), so the list
    ships with the repository (sp_municipalities.json); IBGE is only queried
    if that file is missing, and the result is then saved to it."""

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


def _read_coordinates_cache():
    if not COORDINATES_CACHE_FILE.exists():
        return {}
    with open(COORDINATES_CACHE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def _write_coordinates_cache(cache):
    COORDINATES_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(COORDINATES_CACHE_FILE, "w", encoding="utf-8") as file:
        json.dump(cache, file, ensure_ascii=False, indent=2)


def _fetch_coordinates(name):
    response = requests.get(
        ORS_GEOCODE_URL,
        headers={"Authorization": openrouteservice_key},
        params={
            "text": name,
            "boundary.country": "BR",
            "layers": "locality",
            "size": 1,
            **SP_BOUNDING_BOX,
        },
        timeout=10,
    )
    response.raise_for_status()

    features = response.json()["features"]
    if not features or features[0]["properties"].get("region_a") != "SP":
        raise ValueError(f"Coordenadas não encontradas para: {name}")

    return features[0]["geometry"]["coordinates"]


def geocode_city(name):
    """Resolves a São Paulo municipality name to an approximate [lon, lat]
    coordinate through the OpenRouteService geocoder (the same service and
    key already used for distances), restricted to the state of São Paulo.
    This only ever runs for the handful of cities a user actually selects,
    and the result is cached locally afterwards."""

    municipality_id = _municipality_id_by_name(name)
    if municipality_id is None:
        raise ValueError(f"Município não encontrado: {name}")

    cache = _read_coordinates_cache()
    cache_key = str(municipality_id)

    if cache_key in cache:
        return cache[cache_key]

    coordinates = _fetch_coordinates(name)

    cache[cache_key] = coordinates
    _write_coordinates_cache(cache)

    return coordinates


def geocode_cities(names):
    return {name: geocode_city(name) for name in names}
