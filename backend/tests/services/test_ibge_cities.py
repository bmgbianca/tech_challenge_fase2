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


def ors_response(features):
    return ibge_response({"features": features})


def ors_feature(coordinates, region="SP"):
    return {
        "geometry": {"type": "Point", "coordinates": coordinates},
        "properties": {"region_a": region},
    }


class TestGeocodeCity:
    @pytest.fixture
    def ors(self):
        return ors_response([ors_feature([-47.06, -22.9])])

    @pytest.fixture
    def get(self, cache_files, ors):
        def fake_get(url, **kwargs):
            if url == ibge_cities.IBGE_SP_MUNICIPALITIES_URL:
                return ibge_response(MUNICIPALITIES_PAYLOAD)
            return ors

        with patch.object(ibge_cities.requests, "get", side_effect=fake_get) as get:
            yield get

    def ors_calls(self, get):
        return [c for c in get.call_args_list if c.args[0] == ibge_cities.ORS_GEOCODE_URL]

    def test_returns_the_coordinates_given_by_the_geocoder(self, get):
        assert ibge_cities.geocode_city("Campinas") == [-47.06, -22.9]

    def test_municipality_name_ignores_case(self, get):
        assert ibge_cities.geocode_city("campinas") == [-47.06, -22.9]

    def test_query_is_restricted_to_the_state_of_sao_paulo(self, get):
        ibge_cities.geocode_city("Campinas")

        params = self.ors_calls(get)[0].kwargs["params"]
        assert params["text"] == "Campinas"
        assert params["boundary.country"] == "BR"
        assert params["boundary.rect.min_lat"] == ibge_cities.SP_BOUNDING_BOX[
            "boundary.rect.min_lat"
        ]

    def test_unknown_city_raises_value_error_without_calling_the_geocoder(self, get):
        with pytest.raises(ValueError, match="Atlantis"):
            ibge_cities.geocode_city("Atlantis")

        assert self.ors_calls(get) == []

    def test_no_result_raises_value_error_and_is_not_cached(self, get, cache_files):
        with patch.object(
            ibge_cities.requests, "get", side_effect=[
                ibge_response(MUNICIPALITIES_PAYLOAD), ors_response([]),
            ],
        ):
            with pytest.raises(ValueError, match="Campinas"):
                ibge_cities.geocode_city("Campinas")

        assert not cache_files[1].exists()

    def test_result_from_another_state_is_rejected(self, get):
        get.side_effect = [
            ibge_response(MUNICIPALITIES_PAYLOAD),
            ors_response([ors_feature([-43.0, -22.0], region="RJ")]),
        ]

        with pytest.raises(ValueError, match="Campinas"):
            ibge_cities.geocode_city("Campinas")

    def test_second_geocoding_uses_the_coordinates_cache(self, get):
        ibge_cities.geocode_city("Campinas")
        calls_after_first = len(self.ors_calls(get))

        assert ibge_cities.geocode_city("Campinas") == [-47.06, -22.9]
        assert len(self.ors_calls(get)) == calls_after_first == 1

    def test_geocode_cities_maps_each_name_to_its_coordinates(self, get):
        result = ibge_cities.geocode_cities(["Campinas", "São Paulo"])

        assert result == {
            "Campinas": [-47.06, -22.9],
            "São Paulo": [-47.06, -22.9],
        }
