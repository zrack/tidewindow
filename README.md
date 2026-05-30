# TideWindow

TideWindow is a terminal marine-conditions dashboard for the Gig Harbor and Tacoma Narrows area. It combines NOAA tide/current observations with optional OpenWeather wind data, then scores several local zones for kayaking and fly fishing. It also highlights the best kayak and fishing windows for the next 24 hours from NOAA tide predictions.

![TideWindow terminal dashboard](docs/screenshot.svg)

## Install

Use Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For editable command-line usage:

```bash
pip install -e .
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

Or, after `pip install -e .`:

```bash
tidewindow
```

Press `q` to quit.
Press `a` for all forecast windows, `k` for kayak windows, and `f` for fishing windows.

## Forecast Windows

The forecast panel uses official NOAA tide predictions and estimates current strength from the hourly tide slope. Tide forecast data is labeled as `live`; current forecast data is labeled as `derived` because the app is calculating local planning guidance from the tide curve and zone multipliers.

The app also displays a confidence label. `High` means live tide, current, and wind data with light wind. `Medium` means live tide forecast with derived current guidance. `Low` means seed or fallback data is involved.

## Configuration

Edit `marine_config.py` to change NOAA station IDs, weather coordinates, refresh interval, forecast length, seeded fallback values, or local zone multipliers.

## Test

```bash
python -m unittest discover
```

## Data Sources

- NOAA CO-OPS API for tide and current observations
- NOAA CO-OPS API for tide predictions
- OpenWeather current weather API for optional wind observations

This is a planning aid, not a substitute for marine forecasts, local knowledge, or personal judgment on the water.
