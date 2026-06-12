# TideWindow

TideWindow is a terminal and web marine-conditions dashboard for Puget Sound, South Hood Canal, and Aberdeen-area marine planning. It combines NOAA tide/current observations and predictions with optional OpenWeather wind data, then scores local spots for kayaking and fly fishing. It also highlights the best kayak and fishing windows across a 72-hour planning window.

The web dashboard adds a Tomorrow's Best digest, shareable digest links, calendar export, Leaflet/OpenStreetMap area map, place search, region-aware spot controls, provider diagnostics, risk tolerance, a mobile-friendly daily heatmap, and remembered region/activity preferences. You can search for supported regions or nearby places such as Port Orchard, Aberdeen, Belfair, Union, Chico, or Gorst, see the full spot catalog for the resolved region on the map, then switch to Compact or Standard density when the map feels crowded.

## Visuals

### Web dashboard

![TideWindow desktop web dashboard](docs/web-dashboard-desktop.png)

### Mobile layout

<img src="docs/web-dashboard-mobile.png" alt="TideWindow mobile web dashboard" width="320">

### Terminal dashboard

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
python3 main.py
```

Or, after `pip install -e .`:

```bash
tidewindow
```

To run the web dashboard:

```bash
.venv/bin/uvicorn web_app:app --reload
```

Then open `http://127.0.0.1:8000`.

The web dashboard serves the JavaScript, CSS, and API from the same FastAPI app, so production deployments do not need a separate frontend host or CORS setup.

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Press `q` to quit.
Press `[` and `]` to page through current-condition areas.
Press `a` for all forecast windows, `k` for kayak windows, and `f` for fishing windows.

The terminal dashboard still focuses on the original Gig Harbor/Narrows planning set: Purdy Bridge, Inside Gig Harbor, Fox Island/Hale Passage, Sunrise Beach Park, Narrows Park, Fox Island Fishing Pier, Purdy Sand Spit, and Kopachuck State Park.

The web dashboard starts with all spots for the selected region and uses Compact, Standard, and Full density presets for proportional map marker visibility. The place search accepts supported regions, city-style aliases, common launches, and marine-area names; recognized nearby places route to the closest supported region with a note, such as using South Hood Canal for Belfair. Tomorrow's Best summarizes the strongest kayak and fish windows for the next day, including spot, time, status, tide/current/wind, risk profile, and a short reason. The digest can be opened as a shareable `/digest` page, copied as text, or exported as an `.ics` calendar file; the selected All/Kayak/Fish activity, region, risk tolerance, and spot density carry through those links. The selected region, risk tolerance, density preset, and activity mode are stored in the browser. On phones, the dashboard uses a compact sticky header, stacked summary cards, larger map tap targets, and a scrollable daily heatmap with a selected-hour detail panel.

## Forecast Windows

The forecast panel uses official NOAA tide predictions and NOAA current predictions when available. Tide forecast data is labeled as `live`; current forecast data is labeled as `predicted` when NOAA current predictions are available and `derived` only when TideWindow falls back to estimating current strength from the tide slope. Region provider context can include backup tide/current stations; the fetcher tries those candidates in priority order and the provider panel labels the active station source.

When `OPENWEATHER_API_KEY` has access to OpenWeather One Call 3.0, TideWindow also uses hourly wind forecast points for each window. Forecast wind is labeled as `live`, `fallback`, or `missing`; if hourly wind is unavailable, the app falls back to the current wind value for scoring and says so in the panel. When wind direction is available, spot scoring adjusts wind exposure against each modeled shoreline's fetch, including reviewed spot-specific bearings for high-use regional spots and shoreline-family bearings for the rest.

The app also displays confidence labels. The source confidence summarizes live/predicted/derived/fallback data health, while the provider panel labels station fit with more specific categories such as high station fit, subordinate station fit, sparse current coverage, or river/bar influenced. The provider panel also shows the tide/current priority context, the derived-current fallback, and region-specific caveats.

The web dashboard includes a risk tolerance setting: conservative, standard, or aggressive. Standard preserves the default TideWindow thresholds; conservative flags wind/current risk earlier, while aggressive gives experienced users a wider planning envelope. The heatmap, spot map popups, and full spot details show the active risk profile so the threshold lens stays visible across the app. Spot map popups include current, wind, tide, kayak/fish status, and the local rule copy that used to live in the separate area-details section.

## Configuration

Edit `marine_config.py` to change NOAA station IDs, weather coordinates, refresh interval, forecast length, seeded fallback values, or local zone multipliers.

Runtime environment variables:

```bash
OPENWEATHER_API_KEY=your_api_key_here
TIDEWINDOW_WEB_APP_NAME=TideWindow
TIDEWINDOW_WEB_REFRESH_SECONDS=300
```

`OPENWEATHER_API_KEY` is optional. If it is missing or One Call 3.0 is not active yet, TideWindow labels wind data as fallback or missing and continues running.

## Deployment

TideWindow can run on any Python host that supports ASGI apps, such as Render, Fly.io, Railway, or a small VPS.

Typical build command:

```bash
pip install -r requirements.txt
```

Typical start command:

```bash
uvicorn web_app:app --host 0.0.0.0 --port $PORT
```

For hosts that do not provide `PORT`, use:

```bash
uvicorn web_app:app --host 0.0.0.0 --port 8000
```

Set `OPENWEATHER_API_KEY` in the host's environment settings if you want live OpenWeather wind observations and One Call 3.0 hourly wind forecasts. Set `TIDEWINDOW_WEB_REFRESH_SECONDS` to control how often the browser refreshes the dashboard data; the default is `300` seconds.

Use `/health` for uptime checks. It returns app status, version, timestamp, zone count, forecast length, refresh interval, configured NOAA stations, provider confidence/profile metadata, and whether an OpenWeather key is present. It does not call external providers, so uptime checks stay fast and do not consume API quota.

## Test

```bash
python3 -m unittest discover
```

## Data Sources

- NOAA CO-OPS API for tide and current observations
- NOAA CO-OPS API for tide and current predictions
- OpenWeather current weather API for optional wind observations
- OpenWeather One Call 3.0 API for optional hourly wind forecasts

This is a planning aid, not a substitute for marine forecasts, local knowledge, or personal judgment on the water.
