#!/usr/bin/env python3
"""Task 5 - Weather Dashboard Using a Public REST API.

Consume a public REST API (OpenWeatherMap) to fetch live weather data for a
user-specified city. Uses environment variables for API keys (python-dotenv
recommended) with graceful error handling for invalid city, timeout and failed
requests. Presents results in a clean, readable CLI format.

Covered topics:
    REST APIs | HTTP Methods & Status Codes | JSON Parsing | Secrets Management

Bonus:
    Writing tests with mocking (see test_weather.py).
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any

import requests
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

API_BASE = "https://api.openweathermap.org/data/2.5/weather"
DEFAULT_TIMEOUT = 10


class WeatherError(Exception):
    """Base exception for weather-related errors."""


class MissingAPIKeyError(WeatherError):
    """Raised when the API key is not configured."""


class CityNotFoundError(WeatherError):
    """Raised when the API returns 404 for an unknown city."""


class WeatherAPIError(WeatherError):
    """Raised for other API/request failures."""


@dataclass
class WeatherReport:
    city: str
    country: str
    description: str
    temperature_c: float
    feels_like_c: float
    temp_min_c: float
    temp_max_c: float
    humidity: int
    pressure: int
    wind_speed: float
    wind_deg: int | None

    def __str__(self) -> str:
        lines = [
            "=" * 50,
            f"Weather in {self.city}, {self.country}",
            "=" * 50,
            f"Condition:        {self.description.title()}",
            f"Temperature:      {self.temperature_c:.1f} °C",
            f"Feels like:       {self.feels_like_c:.1f} °C",
            f"Min / Max:        {self.temp_min_c:.1f} °C / {self.temp_max_c:.1f} °C",
            f"Humidity:         {self.humidity}%",
            f"Pressure:         {self.pressure} hPa",
            f"Wind:             {self.wind_speed} m/s{f' ({self.wind_deg}°)' if self.wind_deg is not None else ''}",
            "=" * 50,
        ]
        return "\n".join(lines)


def get_api_key() -> str:
    key = os.getenv("OPENWEATHER_API_KEY") or os.getenv("WEATHER_API_KEY")
    if not key:
        raise MissingAPIKeyError(
            "Missing API key. Set OPENWEATHER_API_KEY (or WEATHER_API_KEY) in environment "
            "or in a .env file. Get a free key at https://openweathermap.org/api"
        )
    return key.strip()


def fetch_weather(city: str, api_key: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> WeatherReport:
    """Fetch current weather for ``city`` from OpenWeatherMap."""
    if not city or not city.strip():
        raise WeatherError("City name cannot be empty.")

    key = api_key or get_api_key()

    params = {"q": city.strip(), "appid": key, "units": "metric"}
    try:
        resp = requests.get(API_BASE, params=params, timeout=timeout)
    except requests.exceptions.Timeout:
        raise WeatherAPIError("Request timed out. Please try again.") from None
    except requests.exceptions.ConnectionError:
        raise WeatherAPIError("Network connection error. Check your internet connection.") from None
    except requests.RequestException as exc:
        raise WeatherAPIError(f"Request failed: {exc}") from None

    if resp.status_code == 404:
        raise CityNotFoundError(f"City '{city}' not found. Check the spelling and try again.")
    if resp.status_code == 401:
        raise WeatherAPIError("Invalid API key. Check your OPENWEATHER_API_KEY.")
    if resp.status_code >= 400:
        try:
            payload = resp.json()
            message = payload.get("message", resp.reason)
        except ValueError:
            message = resp.reason
        raise WeatherAPIError(f"API error ({resp.status_code}): {message}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise WeatherAPIError(f"Invalid JSON response from API: {exc}") from None

    try:
        report = WeatherReport(
            city=data["name"],
            country=data.get("sys", {}).get("country", "??"),
            description=data.get("weather", [{}])[0].get("description", "unknown"),
            temperature_c=float(data["main"]["temp"]),
            feels_like_c=float(data["main"]["feels_like"]),
            temp_min_c=float(data["main"]["temp_min"]),
            temp_max_c=float(data["main"]["temp_max"]),
            humidity=int(data["main"]["humidity"]),
            pressure=int(data["main"]["pressure"]),
            wind_speed=float(data.get("wind", {}).get("speed", 0.0)),
            wind_deg=data.get("wind", {}).get("deg"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherAPIError(f"Unexpected API response format: {exc}") from None

    return report


def main() -> int:
    print("Weather Dashboard (OpenWeatherMap)")
    print("-" * 40)

    try:
        city = input("Enter city name: ").strip()
        report = fetch_weather(city)
        print()
        print(report)
        return 0
    except MissingAPIKeyError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2
    except CityNotFoundError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1
    except WeatherAPIError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except EOFError:
        print()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
