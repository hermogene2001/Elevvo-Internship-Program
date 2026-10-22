# Task 5 — Weather Dashboard Using a Public REST API

**Level 3 · Module 6 · Tools: `requests`, `python-dotenv` (optional)**

Fetches live weather data for a user-specified city from the OpenWeatherMap REST
API, loads the API key from environment variables, handles errors gracefully,
and presents results in a clean CLI format.

**Covered topics:** REST APIs · HTTP Methods & Status Codes · JSON Parsing · Secrets Management

**Bonus implemented:** automated tests with `unittest.mock` (no live network calls required).

## Files

| File | Purpose |
|------|---------|
| `weather.py` | API client, error types, `WeatherReport`, and CLI. |
| `test_weather.py` | Tests with mocked `requests.get`. |
| `.env.example` | Template for your API key. |

## Setup

1. Get a free API key at [openweathermap.org/api](https://openweathermap.org/api).
2. Copy `.env.example` to `.env` and add your key:

```bash
cp .env.example .env
# edit .env: OPENWEATHER_API_KEY=...
```

Or set it directly in your shell:

```bash
# Windows PowerShell
$env:OPENWEATHER_API_KEY="your_key"

# Linux/macOS
export OPENWEATHER_API_KEY="your_key"
```

## Run

```bash
cd task5_weather_dashboard
python weather.py
```

## Error handling

- **Missing key** → `MissingAPIKeyError` with instructions.
- **Invalid city** (404) → `CityNotFoundError`.
- **Invalid key** (401) → clear message.
- **Timeout / connection error** → handled gracefully.
- **Other HTTP errors** → parsed from API response when possible.
- **Malformed JSON / unexpected shape** → caught and reported.

## Tests

```bash
python -m unittest test_weather -v
# or: pytest test_weather.py -v
```

The tests cover a successful fetch, 404, 401, timeout, connection error, empty input, and missing env keys — all via mocking.
