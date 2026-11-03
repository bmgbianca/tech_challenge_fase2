from unittest.mock import MagicMock, patch

import pytest

from backend.services import ibge_cities


@pytest.fixture
def cache_files(tmp_path):
    municipalities = tmp_path / "sp_municipalities.json"
    coordinates = tmp_path / "sp_municipality_coordinates.json"
    with patch.object(ibge_cities, "CACHE_FILE", municipalities), patch.object(
        ibge_cities, "COORDINATES_CACHE_FILE", coordinates
    ):
        yield municipalities, coordinates


def ibge_response(payload):
    response = MagicMock()
    response.json.return_value = payload
    return response


MUNICIPALITIES_PAYLOAD = [
    {"id": 3509502, "nome": "Campinas"},
    {"id": 3550308, "nome": "São Paulo"},
    {"id": 3500105, "nome": "Adamantina"},
]


class TestGetSpMunicipalities:
    def test_fetches_from_ibge_and_sorts_by_name(self, cache_files):
        with patch.object(
            ibge_cities.requests,
            "get",
            return_value=ibge_response(MUNICIPALITIES_PAYLOAD),
        ):
            result = ibge_cities.get_sp_municipalities()

        assert [m["name"] for m in result] == ["Adamantina", "Campinas", "São Paulo"]
        assert result[0] == {"id": 3500105, "name": "Adamantina"}

    def test_second_call_uses_the_local_cache(self, cache_files):
        with patch.object(
            ibge_cities.requests,
            "get",
            return_value=ibge_response(MUNICIPALITIES_PAYLOAD),
        ) as get:
            first = ibge_cities.get_sp_municipalities()
            second = ibge_cities.get_sp_municipalities()

        assert first == second
        get.assert_called_once()

    def test_http_error_is_propagated_and_nothing_is_cached(self, cache_files):
        response = ibge_response([])
        response.raise_for_status.side_effect = RuntimeError("IBGE fora do ar")

        with patch.object(ibge_cities.requests, "get", return_value=response):
            with pytest.raises(RuntimeError):
                ibge_cities.get_sp_municipalities()

        assert not cache_files[0].exists()


class TestPolygonPoints:
    def test_polygon_returns_the_points_of_every_ring(self):
        geometry = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1]]]}

        assert ibge_cities._polygon_points(geometry) == [[0, 0], [1, 0], [1, 1]]

    def test_multipolygon_flattens_all_polygons(self):
        geometry = {
            "type": "MultiPolygon",
            "coordinates": [[[[0, 0], [1, 0]]], [[[5, 5], [6, 6]]]],
        }

        assert ibge_cities._polygon_points(geometry) == [
            [0, 0],
            [1, 0],
            [5, 5],
            [6, 6],
        ]


class TestGeocodeCity:
    @pytest.fixture
    def malha(self):
        # square whose centroid (mean of the points) is [2.0, 4.0]
        return ibge_response(
            {
                "features": [
                    {
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[0, 0], [4, 0], [4, 8], [0, 8]]],
                        }
                    }
                ]
            }
        )

    @pytest.fixture
    def get(self, cache_files, malha):
        def fake_get(url, **kwargs):
            if url == ibge_cities.IBGE_SP_MUNICIPALITIES_URL:
                return ibge_response(MUNICIPALITIES_PAYLOAD)
            return malha

        with patch.object(ibge_cities.requests, "get", side_effect=fake_get) as get:
            yield get

    def test_returns_the_mean_of_the_boundary_points(self, get):
        assert ibge_cities.geocode_city("Campinas") == [2.0, 4.0]

    def test_municipality_name_ignores_case(self, get):
        assert ibge_cities.geocode_city("campinas") == [2.0, 4.0]

    def test_requests_the_boundary_of_the_right_municipality(self, get):
        ibge_cities.geocode_city("Campinas")

        urls = [call.args[0] for call in get.call_args_list]
        assert ibge_cities.IBGE_MALHA_URL.format(id=3509502) in urls

    def test_unknown_city_raises_value_error(self, get):
        with pytest.raises(ValueError, match="Atlantis"):
            ibge_cities.geocode_city("Atlantis")

    def test_second_geocoding_uses_the_coordinates_cache(self, get):
        ibge_cities.geocode_city("Campinas")
        calls_after_first = get.call_count

        assert ibge_cities.geocode_city("Campinas") == [2.0, 4.0]
        assert get.call_count == calls_after_first

    def test_geocode_cities_maps_each_name_to_its_coordinates(self, get):
        result = ibge_cities.geocode_cities(["Campinas", "São Paulo"])

        assert result == {"Campinas": [2.0, 4.0], "São Paulo": [2.0, 4.0]}
