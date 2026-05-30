# TideWindow

TideWindow is a terminal marine-conditions dashboard for the Gig Harbor and Tacoma Narrows area. It combines NOAA tide/current observations with optional OpenWeather wind data, then scores several local zones for kayaking and fly fishing.

![TideWindow terminal dashboard](docs/screenshot.svg)

## Install

Use Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Optional Wind Data

TideWindow can run without an OpenWeather API key. If the key is missing, it uses a default wind value and labels the wind source as fallback data.

Create a `.env` file:

```bash
OPENWEATHER_API_KEY=your_api_key_here
```

## Run

```bash
python main.py
```

Press `q` to quit.

## Configuration

Edit `marine_config.py` to change NOAA station IDs, weather coordinates, refresh interval, seeded fallback values, or local zone multipliers.

## Test

```bash
python -m unittest discover
```

## Data Sources

- NOAA CO-OPS API for tide and current observations
- OpenWeather current weather API for optional wind observations

This is a planning aid, not a substitute for marine forecasts, local knowledge, or personal judgment on the water.
