import asyncio
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static
from noaa_client import NoaaMarineClient
from marine_engine import MarineSafetyEngine
from marine_config import (
    FORECAST_HOURS,
    FORECAST_MAX_WINDOWS_PER_ACTIVITY,
    UPDATE_INTERVAL_SECONDS,
    VISIBLE_ZONE_COUNT,
    ZONES,
)

class LocationColumn(Vertical):
    """A vertical column containing data for a specific location."""
    pass

class MetricBox(Static):
    """A widget for displaying a single metric."""
    pass

class MarineTerminalApp(App):
    """Multi-Zone Marine Telemetry for Gig Harbor."""

    TITLE = "TideWindow"
    SUB_TITLE = "Gig Harbor Marine Windows"

    CSS = """
    Screen { layout: vertical; }
    
    #main-grid {
        layout: horizontal;
        height: 1fr;
    }

    #forecast-panel {
        height: 10;
        border: round magenta;
        margin: 0 1 1 1;
        padding: 1;
    }
    
    .location-column {
        width: 1fr;
        height: 100%;
        border: solid cyan;
        margin: 1;
        padding: 1;
    }
    
    .location-title {
        content-align: center middle;
        text-style: bold;
        height: 3;
        border-bottom: dashed white;
        margin-bottom: 1;
    }
    
    .data-box {
        height: 4;
        margin-bottom: 1;
        border: round white;
        content-align: center middle;
    }
    
    .status-box {
        height: 1fr;
        border: solid white;
        padding: 0 1;
        margin-bottom: 1;
    }

    #source-status {
        height: 3;
        border: round white;
        margin: 0 1;
        content-align: center middle;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit Terminal"),
        ("[", "previous_zone_page", "Prev Areas"),
        ("]", "next_zone_page", "Next Areas"),
        ("a", "forecast_all", "All Windows"),
        ("k", "forecast_kayak", "Kayak Windows"),
        ("f", "forecast_fish", "Fishing Windows"),
        ("d", "toggle_diagnostics", "Diagnostics"),
    ]

    def __init__(self):
        super().__init__()
        self.noaa = NoaaMarineClient()
        self.engine = MarineSafetyEngine()
        self.forecast_filter = "All"
        self.forecast_windows = []
        self.forecast_data = {}
        self.confidence = {}
        self.show_diagnostics = False
        self.zone_page = 0
        self.current_zones = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Horizontal(id="main-grid"):
            for slot in range(VISIBLE_ZONE_COUNT):
                ui_prefix = f"zone{slot}"
                with LocationColumn(classes="location-column", id=f"col-{ui_prefix}"):
                    yield Static("Loading...", id=f"{ui_prefix}-title", classes="location-title")
                    yield MetricBox("Loading...", id=f"{ui_prefix}-metrics", classes="data-box")
                    yield MetricBox("Loading...", id=f"{ui_prefix}-kayak", classes="status-box")
                    yield MetricBox("Loading...", id=f"{ui_prefix}-fish", classes="status-box")

        yield Static("Forecast loading...", id="forecast-panel")
        yield Static("Waiting for telemetry...", id="source-status")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self.update_telemetry())
        self.set_interval(UPDATE_INTERVAL_SECONDS, lambda: self.run_worker(self.update_telemetry()))

    async def update_telemetry(self) -> None:
        data, forecast = await asyncio.gather(
            self.noaa.fetch_telemetry(),
            self.noaa.fetch_forecast(),
        )
        
        # Get localized data from the physics engine
        zones = self.engine.get_zone_telemetry(
            data['current_knots'], 
            data['tide_feet'], 
            data['wind_knots']
        )

        status = self._format_source_status(data)
        self.query_one("#source-status", Static).update(status)

        windows = self.engine.build_forecast_windows(
            forecast.get("predictions", []),
            data["wind_knots"],
            wind_predictions=forecast.get("wind_predictions", []),
            current_predictions=forecast.get("current_predictions", []),
            current_source=forecast.get("sources", {}).get("current", "derived"),
            wind_source=forecast.get("sources", {}).get("wind", "fallback"),
            max_windows_per_activity=FORECAST_MAX_WINDOWS_PER_ACTIVITY,
        )
        self.forecast_windows = windows
        self.forecast_data = forecast
        self.confidence = self.engine.evaluate_confidence(
            data,
            forecast,
            data["wind_knots"],
        )
        self._render_forecast()

        self.current_zones = zones
        self._render_current_conditions()

    def action_previous_zone_page(self) -> None:
        page_count = self._zone_page_count()
        self.zone_page = (self.zone_page - 1) % page_count
        self._render_current_conditions()

    def action_next_zone_page(self) -> None:
        page_count = self._zone_page_count()
        self.zone_page = (self.zone_page + 1) % page_count
        self._render_current_conditions()

    def action_forecast_all(self) -> None:
        self.forecast_filter = "All"
        self._render_forecast()

    def action_forecast_kayak(self) -> None:
        self.forecast_filter = "Kayak"
        self._render_forecast()

    def action_forecast_fish(self) -> None:
        self.forecast_filter = "Fish"
        self._render_forecast()

    def action_toggle_diagnostics(self) -> None:
        self.show_diagnostics = not self.show_diagnostics
        self._render_forecast()

    def _render_forecast(self) -> None:
        self.query_one("#forecast-panel", Static).update(
            self._format_forecast(
                self.forecast_windows,
                self.forecast_data,
                self.confidence,
            )
        )

    def _render_current_conditions(self) -> None:
        if not self.current_zones:
            return

        visible_zone_ids = self._visible_zone_ids()
        for slot in range(VISIBLE_ZONE_COUNT):
            ui_prefix = f"zone{slot}"
            if slot >= len(visible_zone_ids):
                self._clear_column(ui_prefix)
                continue

            zone_id = visible_zone_ids[slot]
            zone_data = self.current_zones[zone_id]
            zone_config = ZONES[zone_id]
            self._update_column(
                zone_id,
                zone_data,
                ui_prefix,
                f"{zone_config['title']}\n{self._zone_page_label()}",
            )

    def _update_column(self, zone_id: str, zone_data: dict, ui_prefix: str, title: str) -> None:
        self.query_one(f"#{ui_prefix}-title", Static).update(title)

        metrics = (
            f"Current {zone_data['current']:.2f} kt\n"
            f"Wind {zone_data['wind']:.1f} kt | Tide {zone_data['tide']:.1f} ft"
        )
        self.query_one(f"#{ui_prefix}-metrics", MetricBox).update(metrics)

        kayak = self.engine.evaluate_kayaking(zone_id, zone_data['current'], zone_data['wind'])
        k_box = self.query_one(f"#{ui_prefix}-kayak", MetricBox)
        k_box.update(f"[{kayak['color']}]KAYAK: {kayak['status']}[/]\n{kayak['note']}")
        k_box.styles.border = ("solid", kayak["color"])

        fish = self.engine.evaluate_fly_fishing(zone_id, zone_data['current'], zone_data['tide'])
        f_box = self.query_one(f"#{ui_prefix}-fish", MetricBox)
        f_box.update(f"[{fish['color']}]FISH: {fish['status']}[/]\n{fish['note']}")
        f_box.styles.border = ("solid", fish["color"])

    def _clear_column(self, ui_prefix: str) -> None:
        self.query_one(f"#{ui_prefix}-title", Static).update("")
        self.query_one(f"#{ui_prefix}-metrics", MetricBox).update("")
        self.query_one(f"#{ui_prefix}-kayak", MetricBox).update("")
        self.query_one(f"#{ui_prefix}-fish", MetricBox).update("")

    def _format_forecast(self, windows: list, forecast: dict, confidence: dict) -> str:
        sources = forecast.get("sources", {})
        confidence_level = confidence.get("level", "Unknown")
        confidence_color = confidence.get("color", "white")
        title = (
            f"[bold]NEXT {FORECAST_HOURS} HOURS: BEST WINDOWS[/] "
            f"[dim]Mode: {self.forecast_filter} | Tide: {sources.get('tide', 'unknown')} | "
            f"Current: {sources.get('current', 'unknown')} | Wind: {sources.get('wind', 'unknown')} | "
            f"Confidence: [{confidence_color}]{confidence_level}[/][/]"
        )

        visible_windows = self._filter_forecast_windows(windows)
        if not visible_windows:
            lines = [title, "[yellow]No forecast windows available.[/]"]
            return "\n".join(lines + self._diagnostic_lines(forecast, confidence))

        lines = [title]
        for window in visible_windows:
            zone_name = window["zone_title"].split(" (")[0].title()
            lines.append(
                f"[bold]{window['activity']}[/] {window['start']:%a %I%p}-{window['end']:%I%p} "
                f"| {zone_name} | {window['status']} | {window['phase']} | "
                f"{window['current']:.1f} kt current ({window.get('current_source', 'derived')}), "
                f"{window['wind']:.0f} kt wind ({window['wind_source']})"
            )

        lines.extend(self._diagnostic_lines(forecast, confidence))
        return "\n".join(lines)

    def _diagnostic_lines(self, forecast: dict, confidence: dict) -> list:
        notice = self._compact_notice(forecast)
        if not self.show_diagnostics:
            return [f"[dim]{notice} Press d for details.[/]"] if notice else []

        lines = []
        if notice:
            lines.append(f"[yellow]{notice}[/]")
        if forecast.get("fallback_reason"):
            lines.append(f"[dim]{forecast['fallback_reason']}[/]")
        if forecast.get("wind_fallback_reason"):
            lines.append(f"[dim]{forecast['wind_fallback_reason']}[/]")
        elif confidence.get("note"):
            lines.append(f"[dim]{confidence['note']}[/]")
        return lines

    def _compact_notice(self, forecast: dict) -> str:
        if forecast.get("fallback_reason"):
            return "Forecast fallback active."

        wind_notice = forecast.get("wind_fallback_reason")
        if wind_notice:
            return "Hourly wind unavailable; using current wind."

        return ""

    def _format_source_status(self, data: dict) -> str:
        sources = data.get("sources", {})
        status = (
            f"Updated: {data.get('updated_at', 'now')} | "
            f"Tide: {sources.get('tide', 'unknown')} | "
            f"Current: {sources.get('current', 'unknown')} | "
            f"Wind: {sources.get('wind', 'unknown')}"
        )
        if data.get("fallback_reason"):
            status += " | Notice: live NOAA telemetry unavailable"
        return status

    def _filter_forecast_windows(self, windows: list) -> list:
        if self.forecast_filter == "All":
            return windows
        return [
            window for window in windows
            if window["activity"] == self.forecast_filter
        ]

    def _visible_zone_ids(self) -> list:
        zone_ids = list(ZONES.keys())
        start = self.zone_page * VISIBLE_ZONE_COUNT
        return zone_ids[start:start + VISIBLE_ZONE_COUNT]

    def _zone_page_count(self) -> int:
        return (len(ZONES) + VISIBLE_ZONE_COUNT - 1) // VISIBLE_ZONE_COUNT

    def _zone_page_label(self) -> str:
        return f"Page {self.zone_page + 1}/{self._zone_page_count()}"
