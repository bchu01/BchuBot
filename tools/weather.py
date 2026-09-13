import json
import urllib.parse
import urllib.request


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 8
MAX_LOCATION_LENGTH = 100

_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Icy fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    56: "Light freezing drizzle",
    57: "Freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Light rain showers",
    81: "Rain showers",
    82: "Heavy rain showers",
    85: "Light snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}


def get_weather(location):
    """Get the current weather for a named location."""
    if not isinstance(location, str) or not location.strip():
        return {"ok": False, "error": "A location name is required."}

    location = location.strip()
    if len(location) > MAX_LOCATION_LENGTH:
        return {"ok": False, "error": "That location name is too long."}

    try:
        place = _geocode(location)
        if place is None:
            return {"ok": False, "error": f"Could not find that location: {location}"}

        current = _fetch_current(place["latitude"], place["longitude"])
        if current is None:
            return {"ok": False, "error": "Weather data was unavailable."}

        temperature_f = current["temperature_2m"]
        return {
            "ok": True,
            "location": place["name"],
            "temperature_f": round(temperature_f),
            "temperature_c": round((temperature_f - 32) * 5 / 9, 1),
            "conditions": _WEATHER_CODES.get(
                current.get("weather_code"),
                "Unknown conditions",
            ),
            "humidity_percent": current.get("relative_humidity_2m"),
            "wind_mph": round(current.get("wind_speed_10m", 0)),
        }
    except Exception:
        return {"ok": False, "error": "Could not get the weather."}


def _geocode(location):
    data = _get_json(
        GEOCODING_URL,
        {
            "name": location,
            "count": 1,
            "language": "en",
            "format": "json",
        },
    )
    results = data.get("results") or []
    if not results:
        return None

    result = results[0]
    latitude = result.get("latitude")
    longitude = result.get("longitude")
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        return None

    parts = [result.get("name"), result.get("admin1"), result.get("country")]
    display_name = ", ".join(part for part in parts if part)
    return {
        "name": display_name or location,
        "latitude": latitude,
        "longitude": longitude,
    }


def _fetch_current(latitude, longitude):
    data = _get_json(
        FORECAST_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,relative_humidity_2m,"
                "weather_code,wind_speed_10m"
            ),
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "timezone": "auto",
        },
    )
    current = data.get("current")
    if not isinstance(current, dict) or "temperature_2m" not in current:
        return None
    return current


def _get_json(url, params):
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={"User-Agent": "BchuBot/0.1 (personal assistant)"},
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode())
