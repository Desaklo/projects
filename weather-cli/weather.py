#!/usr/bin/env python3
"""Current weather for a city, via the Open-Meteo API. No API key required."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, NoReturn

EXIT_OK = 0
EXIT_USER = 1
EXIT_ERROR = 2

USER_AGENT = "weather-cli/1.0 (+https://github.com/Desaklo/projects)"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 20

CURRENT_VARS = (
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
)

# WMO weather interpretation codes used by Open-Meteo.
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

COMPASS = (
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
)

# Open-Meteo labels miles per hour as "mp/h". Show the usual abbreviation.
WIND_UNIT_LABELS = {
    "km/h": "km/h",
    "mp/h": "mph",
    "mph": "mph",
    "m/s": "m/s",
    "kn": "kn",
}

RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class _TransientError(Exception):
    """A timeout or temporary HTTP failure worth one retry."""


def fail(message: str, code: int) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def fetch_json(url: str) -> dict[str, Any]:
    message = "cannot reach weather service"
    for attempt in range(2):
        try:
            return _fetch_json_once(url)
        except _TransientError as exc:
            message = str(exc)
            if attempt == 0:
                time.sleep(0.6)
    fail(message, EXIT_ERROR)


def _fetch_json_once(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read().decode(charset)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        reason = _error_reason(detail)
        message = f"weather service returned HTTP {exc.code}"
        if reason:
            message = f"{message}: {reason}"
        if exc.code in RETRYABLE_STATUS:
            raise _TransientError(message) from exc
        fail(message, EXIT_ERROR)
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise _TransientError("weather service timed out") from exc
        fail(f"cannot reach weather service: {exc.reason}", EXIT_ERROR)
    except TimeoutError as exc:
        raise _TransientError("weather service timed out") from exc
    except OSError as exc:
        fail(f"cannot reach weather service: {exc}", EXIT_ERROR)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        fail("weather service returned invalid JSON", EXIT_ERROR)
    if not isinstance(data, dict):
        fail("weather service returned an unexpected response", EXIT_ERROR)
    if data.get("error") is True:
        reason = data.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            reason = "request failed"
        fail(f"weather service: {reason.strip()}", EXIT_ERROR)
    return data


def _error_reason(body: str) -> str:
    if not body:
        return ""
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body[:200]
    if isinstance(payload, dict):
        reason = payload.get("reason")
        if isinstance(reason, str) and reason.strip():
            return reason.strip()[:200]
    return body[:200]


def search_places(name: str, country: str | None) -> list[dict[str, Any]]:
    params = {
        "name": name,
        "count": "10",
        "language": "en",
        "format": "json",
    }
    if country:
        params["countryCode"] = country
    data = fetch_json(f"{GEOCODE_URL}?{urllib.parse.urlencode(params)}")
    results = data.get("results") or []
    if not isinstance(results, list):
        fail("weather service returned an unexpected response", EXIT_ERROR)

    places: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        latitude = item.get("latitude")
        longitude = item.get("longitude")
        if isinstance(latitude, bool) or not isinstance(latitude, (int, float)):
            continue
        if isinstance(longitude, bool) or not isinstance(longitude, (int, float)):
            continue
        code = item.get("country_code")
        if country and (not isinstance(code, str) or code.upper() != country):
            continue
        places.append(item)
    return places


def fetch_weather(place: dict[str, Any], units: str) -> dict[str, Any]:
    temperature_unit, wind_unit = (
        ("fahrenheit", "mph") if units == "fahrenheit" else ("celsius", "kmh")
    )
    params = {
        "latitude": f"{float(place['latitude']):.6f}",
        "longitude": f"{float(place['longitude']):.6f}",
        "current": ",".join(CURRENT_VARS),
        "temperature_unit": temperature_unit,
        "wind_speed_unit": wind_unit,
        "timezone": "auto",
    }
    return fetch_json(f"{FORECAST_URL}?{urllib.parse.urlencode(params)}")


def place_label(place: dict[str, Any]) -> str:
    name = _clean(place.get("name"))
    admin = _clean(place.get("admin1"))
    country = _clean(place.get("country"))
    parts: list[str] = []
    if name:
        parts.append(name)
    if admin and admin != name:
        parts.append(admin)
    elif admin and name and country and country != name:
        # Keep both when the city and region share a name.
        parts.append(admin)
    if country and country not in parts:
        parts.append(country)
    return ", ".join(parts) if parts else "Unknown place"


def _clean(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def wind_unit_label(unit: str) -> str:
    return WIND_UNIT_LABELS.get(unit, unit)


def condition_text(code: Any) -> str:
    if isinstance(code, bool) or not isinstance(code, (int, float)):
        return "Unknown conditions"
    return WEATHER_CODES.get(int(code), f"Weather code {int(code)}")


def compass(degrees: Any) -> str | None:
    if isinstance(degrees, bool) or not isinstance(degrees, (int, float)):
        return None
    index = int((float(degrees) % 360) / 22.5 + 0.5) % 16
    return COMPASS[index]


def format_number(value: Any, digits: int) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "n/a"
    return f"{float(value):.{digits}f}"


def current_block(forecast: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    current = forecast.get("current")
    units = forecast.get("current_units")
    if not isinstance(current, dict) or not isinstance(units, dict):
        fail("weather service returned an unexpected response", EXIT_ERROR)
    return current, units


def render_text(place: dict[str, Any], forecast: dict[str, Any], extra_count: int) -> str:
    current, units = current_block(forecast)
    temp_unit = _unit(units, "temperature_2m")
    wind_unit = wind_unit_label(_unit(units, "wind_speed_10m"))
    precip_unit = _unit(units, "precipitation")
    humidity_unit = _unit(units, "relative_humidity_2m") or "%"

    temperature = format_number(current.get("temperature_2m"), 1)
    feels_like = format_number(current.get("apparent_temperature"), 1)
    humidity = format_number(current.get("relative_humidity_2m"), 0)
    if humidity_unit == "%":
        humidity_text = f"{humidity}%"
    else:
        humidity_text = f"{humidity} {humidity_unit}".strip()

    wind = format_number(current.get("wind_speed_10m"), 1)
    wind_text = f"{wind} {wind_unit}".strip()
    direction = compass(current.get("wind_direction_10m"))
    if direction:
        wind_text = f"{wind_text} from {direction}"

    observed = observed_at(current, forecast)
    precipitation = format_number(current.get("precipitation"), 1)
    precip_text = f"{precipitation} {precip_unit}".strip()

    lines = [
        place_label(place),
        condition_text(current.get("weather_code")),
        f"Temperature: {temperature} {temp_unit} (feels like {feels_like} {temp_unit})".strip(),
        f"Humidity: {humidity_text}",
        f"Wind: {wind_text}",
        f"Precipitation: {precip_text}",
        f"Observed: {observed}",
    ]
    if extra_count:
        noun = "match" if extra_count == 1 else "matches"
        lines.append("")
        lines.append(
            f"{extra_count} other {noun}. Run with --list to choose a different place."
        )
    lines.append("")
    lines.append("Data: Open-Meteo (https://open-meteo.com/)")
    return "\n".join(lines)


def render_json(place: dict[str, Any], forecast: dict[str, Any]) -> str:
    current, units = current_block(forecast)
    payload = {
        "place": place_label(place),
        "country_code": place.get("country_code"),
        "latitude": place.get("latitude"),
        "longitude": place.get("longitude"),
        "condition": condition_text(current.get("weather_code")),
        "weather_code": current.get("weather_code"),
        "temperature": current.get("temperature_2m"),
        "temperature_unit": units.get("temperature_2m"),
        "apparent_temperature": current.get("apparent_temperature"),
        "humidity": current.get("relative_humidity_2m"),
        "precipitation": current.get("precipitation"),
        "precipitation_unit": units.get("precipitation"),
        "wind_speed": current.get("wind_speed_10m"),
        "wind_speed_unit": wind_unit_label(_unit(units, "wind_speed_10m")),
        "wind_direction": current.get("wind_direction_10m"),
        "wind_compass": compass(current.get("wind_direction_10m")),
        "observed_at": current.get("time"),
        "timezone": forecast.get("timezone"),
        "source": "Open-Meteo",
        "source_url": "https://open-meteo.com/",
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def render_list(places: list[dict[str, Any]]) -> str:
    width = len(str(len(places)))
    lines = [
        f"{index:>{width}}  {place_label(place)}"
        for index, place in enumerate(places, start=1)
    ]
    return "\n".join(lines)


def observed_at(current: dict[str, Any], forecast: dict[str, Any]) -> str:
    raw = current.get("time")
    if not isinstance(raw, str) or not raw.strip():
        return "unknown"
    text = raw.strip().replace("T", " ")
    zone = forecast.get("timezone_abbreviation")
    if isinstance(zone, str) and zone.strip():
        return f"{text} {zone.strip()}"
    return text


def _unit(units: dict[str, Any], key: str) -> str:
    value = units.get(key)
    if isinstance(value, str):
        return value.strip()
    return ""


def normalize_units(value: str) -> str:
    if value in {"f", "fahrenheit"}:
        return "fahrenheit"
    return "celsius"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weather.py",
        description=(
            "Show the current weather for a city. "
            "Uses the free Open-Meteo API and does not need an API key."
        ),
    )
    parser.add_argument(
        "city",
        nargs="+",
        help="City name. Separate words are joined, so New York works quoted or not",
    )
    parser.add_argument(
        "--units",
        choices=("celsius", "c", "fahrenheit", "f"),
        default="celsius",
        help="Temperature units (default: celsius). Fahrenheit also reports wind in mph.",
    )
    parser.add_argument(
        "--country",
        metavar="CC",
        help="Limit the search to a two-letter country code, for example US or DE",
    )
    parser.add_argument(
        "--pick",
        type=int,
        metavar="N",
        help="Use match number N from the search results (see --list)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List matching places and exit without fetching weather",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the weather as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list and args.json:
        parser.error("--list and --json cannot be used together")

    city = " ".join(args.city).strip()
    if not city:
        fail("city name is empty", EXIT_USER)

    country: str | None = None
    if args.country is not None:
        country = args.country.strip().upper()
        if len(country) != 2 or not country.isalpha():
            fail("country must be a two-letter code such as US", EXIT_USER)

    if args.pick is not None and args.pick < 1:
        fail("--pick must be 1 or greater", EXIT_USER)

    places = search_places(city, country)
    if not places:
        where = f" in {country}" if country else ""
        fail(f"no places found for {city!r}{where}", EXIT_USER)

    if args.list:
        print(render_list(places))
        return EXIT_OK

    index = (args.pick or 1) - 1
    if index >= len(places):
        noun = "match" if len(places) == 1 else "matches"
        fail(
            f"only {len(places)} {noun} for {city!r}; --pick {args.pick} is out of range",
            EXIT_USER,
        )

    place = places[index]
    forecast = fetch_weather(place, normalize_units(args.units))
    if args.json:
        sys.stdout.write(render_json(place, forecast))
        return EXIT_OK

    extra = 0 if args.pick else max(0, len(places) - 1)
    print(render_text(place, forecast, extra))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
