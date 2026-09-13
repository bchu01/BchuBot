import unittest
from unittest.mock import patch

from tools.weather import FORECAST_URL, GEOCODING_URL, get_weather


GEOCODE_RESPONSE = {
    "results": [
        {
            "name": "Boston",
            "latitude": 42.35843,
            "longitude": -71.05977,
            "admin1": "Massachusetts",
            "country": "United States",
        }
    ]
}

FORECAST_RESPONSE = {
    "current": {
        "temperature_2m": 64.2,
        "relative_humidity_2m": 61,
        "weather_code": 2,
        "wind_speed_10m": 8.4,
    }
}


def fake_get_json(url, params):
    if url == GEOCODING_URL:
        return GEOCODE_RESPONSE
    if url == FORECAST_URL:
        return FORECAST_RESPONSE
    raise AssertionError(f"Unexpected URL: {url}")


class WeatherTests(unittest.TestCase):
    def test_requires_a_location(self):
        self.assertEqual(
            get_weather(""),
            {"ok": False, "error": "A location name is required."},
        )
        self.assertEqual(
            get_weather(None),
            {"ok": False, "error": "A location name is required."},
        )

    def test_rejects_long_location_names(self):
        result = get_weather("x" * 101)
        self.assertEqual(
            result,
            {"ok": False, "error": "That location name is too long."},
        )

    @patch("tools.weather._get_json", side_effect=fake_get_json)
    def test_returns_current_conditions(self, _mock_get_json):
        result = get_weather("Boston")
        self.assertEqual(
            result,
            {
                "ok": True,
                "location": "Boston, Massachusetts, United States",
                "temperature_f": 64,
                "temperature_c": 17.9,
                "conditions": "Partly cloudy",
                "humidity_percent": 61,
                "wind_mph": 8,
            },
        )

    @patch("tools.weather._get_json", return_value={"results": []})
    def test_unknown_location(self, _mock_get_json):
        result = get_weather("NotARealCityXYZ")
        self.assertEqual(
            result,
            {"ok": False, "error": "Could not find that location: NotARealCityXYZ"},
        )

    @patch("tools.weather._get_json", side_effect=OSError("network down"))
    def test_network_failure(self, _mock_get_json):
        result = get_weather("Boston")
        self.assertEqual(
            result,
            {"ok": False, "error": "Could not get the weather."},
        )


if __name__ == "__main__":
    unittest.main()
