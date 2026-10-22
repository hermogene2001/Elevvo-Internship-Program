#!/usr/bin/env python3
"""Tests for weather dashboard - uses mocking so no live network calls.

Run with:
    python -m unittest test_weather -v
    pytest test_weather.py -v
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from weather import (
    CityNotFoundError,
    MissingAPIKeyError,
    WeatherAPIError,
    WeatherReport,
    fetch_weather,
    get_api_key,
)


SAMPLE_RESPONSE = {
    "name": "Cairo",
    "sys": {"country": "EG"},
    "weather": [{"description": "clear sky"}],
    "main": {"temp": 25.4, "feels_like": 26.1, "temp_min": 24.0, "temp_max": 27.0, "humidity": 40, "pressure": 1013},
    "wind": {"speed": 3.5, "deg": 180},
}


class TestGetAPIKey(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    def test_missing_key_raises(self) -> None:
        with self.assertRaises(MissingAPIKeyError):
            get_api_key()

    @patch.dict("os.environ", {"OPENWEATHER_API_KEY": "test123"}, clear=True)
    def test_reads_openweather_key(self) -> None:
        self.assertEqual(get_api_key(), "test123")


class TestFetchWeather(unittest.TestCase):
    @patch("weather.requests.get")
    def test_successful_fetch(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = SAMPLE_RESPONSE
        mock_get.return_value = mock_resp

        report = fetch_weather("Cairo", api_key="fake-key")

        self.assertIsInstance(report, WeatherReport)
        self.assertEqual(report.city, "Cairo")
        self.assertEqual(report.country, "EG")
        self.assertEqual(report.temperature_c, 25.4)
        self.assertEqual(report.humidity, 40)

    @patch("weather.requests.get")
    def test_city_not_found(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        with self.assertRaises(CityNotFoundError):
            fetch_weather("NowhereCity", api_key="fake-key")

    @patch("weather.requests.get")
    def test_invalid_key(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp

        with self.assertRaises(WeatherAPIError):
            fetch_weather("Cairo", api_key="bad-key")

    @patch("weather.requests.get")
    def test_timeout(self, mock_get: MagicMock) -> None:
        import requests as req

        mock_get.side_effect = req.exceptions.Timeout

        with self.assertRaises(WeatherAPIError):
            fetch_weather("Cairo", api_key="fake-key")

    @patch("weather.requests.get")
    def test_connection_error(self, mock_get: MagicMock) -> None:
        import requests as req

        mock_get.side_effect = req.exceptions.ConnectionError

        with self.assertRaises(WeatherAPIError):
            fetch_weather("Cairo", api_key="fake-key")

    def test_empty_city(self) -> None:
        with self.assertRaises(Exception):
            fetch_weather("   ", api_key="fake-key")


if __name__ == "__main__":
    unittest.main(verbosity=2)
