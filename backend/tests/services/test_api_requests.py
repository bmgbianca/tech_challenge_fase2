from unittest.mock import MagicMock, patch

from backend.services.api_requests import fetch_distances


class TestFetchDistances:
    def test_returns_parsed_json_on_success(self):
        fake_response = MagicMock()
        fake_response.json.return_value = {
            "distances": [[0, 10], [10, 0]],
            "durations": [[0, 5], [5, 0]],
        }

        with patch(
            "backend.services.api_requests.requests.post", return_value=fake_response
        ) as mock_post:
            result = fetch_distances([["-46.63", "-23.54"], ["-47.05", "-22.90"]])

        mock_post.assert_called_once()
        assert result == {
            "distances": [[0, 10], [10, 0]],
            "durations": [[0, 5], [5, 0]],
        }

    def test_returns_none_when_request_raises(self):
        with patch(
            "backend.services.api_requests.requests.post",
            side_effect=Exception("network error"),
        ):
            result = fetch_distances([["-46.63", "-23.54"]])

        assert result is None

    def test_sends_locations_and_metrics_in_payload(self):
        fake_response = MagicMock()
        fake_response.json.return_value = {}
        locations = [["-46.63", "-23.54"], ["-47.05", "-22.90"]]

        with patch(
            "backend.services.api_requests.requests.post", return_value=fake_response
        ) as mock_post:
            fetch_distances(locations)

        _, kwargs = mock_post.call_args
        assert kwargs["json"]["locations"] == locations
        assert kwargs["json"]["metrics"] == ["distance", "duration"]
