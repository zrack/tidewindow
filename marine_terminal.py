import asyncio
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static
from noaa_client import NoaaMarineClient
from marine_engine import MarineSafetyEngine
from marine_config import FORECAST_MAX_WINDOWS_PER_ACTIVITY, UPDATE_INTERVAL_SECONDS, ZONES

class LocationColumn(Vertical):
    """A vertical column containing data for a specific location."""
    pass

class MetricBox(Static):
    """A widget for displaying a single metric."""
    pass

class MarineTerminalApp(App):
    """Multi-Zone Marine Telemetry for Gig Harbor."""

    CSS = """
    Screen { layout: vertical; }
    
    #main-grid {
        layout: horizontal;
        height: 1fr;
    }

    #forecast-panel {
        height: 9;
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
        padding: 1;
        margin-bottom: 1;
    }

    #source-status {
        height: 3;
        border: round white;
        margin: 0 1;
        content-align: center middle;
    }
    """

    BINDINGS = [("q", "quit", "Quit Terminal")]

    def __init__(self):
        super().__init__()
        self.noaa = NoaaMarineClient()
        self.engine = MarineSafetyEngine()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Horizontal(id="main-grid"):
            for zone_config in ZONES.values():
                ui_prefix = zone_config["ui_prefix"]
                with LocationColumn(classes="location-column", id=f"col-{ui_prefix}"):
                    yield Static(zone_config["title"], classes="location-title")
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

        sources = data.get("sources", {})
        status = (
            f"Updated: {data.get('updated_at', 'now')} | "
            f"Tide: {sources.get('tide', 'unknown')} | "
            f"Current: {sources.get('current', 'unknown')} | "
            f"Wind: {sources.get('wind', 'unknown')}"
        )
        if data.get("fallback_reason"):
            status += f" | Notice: {data['fallback_reason']}"
        self.query_one("#source-status", Static).update(status)

        windows = self.engine.build_forecast_windows(
            forecast.get("predictions", []),
            data["wind_knots"],
            max_windows_per_activity=FORECAST_MAX_WINDOWS_PER_ACTIVITY,
        )
        self.query_one("#forecast-panel", Static).update(
            self._format_forecast(windows, forecast)
        )

        # Helper function to update a specific column
        def update_column(zone_id: str, zone_data: dict, ui_prefix: str):
            # Update raw metrics
            metrics = f"Current: {zone_data['current']:.2f} kts | Wind: {zone_data['wind']:.1f} kts | Tide: {zone_data['tide']:.1f} ft"
            self.query_one(f"#{ui_prefix}-metrics", MetricBox).update(metrics)
            
            # Evaluate and update Kayak
            kayak = self.engine.evaluate_kayaking(zone_id, zone_data['current'], zone_data['wind'])
            k_box = self.query_one(f"#{ui_prefix}-kayak", MetricBox)
            k_box.update(f"[{kayak['color']}]KAYAKING: {kayak['status']}[/]\n\n{kayak['note']}")
            k_box.styles.border = ("solid", kayak["color"])

            # Evaluate and update Fish
            fish = self.engine.evaluate_fly_fishing(zone_id, zone_data['current'], zone_data['tide'])
            f_box = self.query_one(f"#{ui_prefix}-fish", MetricBox)
            f_box.update(f"[{fish['color']}]FLY FISHING: {fish['status']}[/]\n\n{fish['note']}")
            f_box.styles.border = ("solid", fish["color"])

        # Push updates to the screen
        for zone_id, zone_config in ZONES.items():
            update_column(zone_id, zones[zone_id], zone_config["ui_prefix"])

    def _format_forecast(self, windows: list, forecast: dict) -> str:
        sources = forecast.get("sources", {})
        title = (
            "[bold]NEXT 24 HOURS: BEST WINDOWS[/] "
            f"[dim]Tide: {sources.get('tide', 'unknown')} | Current: {sources.get('current', 'unknown')}[/]"
        )
        if forecast.get("fallback_reason"):
            title += f"\n[yellow]Forecast notice: {forecast['fallback_reason']}[/]"

        if not windows:
            return f"{title}\n[yellow]No forecast windows available.[/]"

        lines = [title]
        for window in windows:
            zone_name = window["zone_title"].split(" (")[0].title()
            lines.append(
                f"[bold]{window['activity']}[/] {window['start']:%a %I%p}-{window['end']:%I%p} "
                f"| {zone_name} | {window['status']} | {window['phase']} | "
                f"{window['current']:.1f} kt, {window['wind']:.0f} kt wind"
            )

        return "\n".join(lines)
