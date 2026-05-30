import asyncio
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static
from noaa_client import NoaaMarineClient
from marine_engine import MarineSafetyEngine

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
    """

    BINDINGS = [("q", "quit", "Quit Terminal")]

    def __init__(self):
        super().__init__()
        self.noaa = NoaaMarineClient()
        self.engine = MarineSafetyEngine()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Horizontal(id="main-grid"):
            # Column 1: Purdy Bridge
            with LocationColumn(classes="location-column", id="col-purdy"):
                yield Static("PURDY BRIDGE (HENDERSON BAY)", classes="location-title")
                yield MetricBox("Loading...", id="purdy-metrics", classes="data-box")
                yield MetricBox("Loading...", id="purdy-kayak", classes="status-box")
                yield MetricBox("Loading...", id="purdy-fish", classes="status-box")

            # Column 2: Inside Gig Harbor
            with LocationColumn(classes="location-column", id="col-harbor"):
                yield Static("INSIDE GIG HARBOR", classes="location-title")
                yield MetricBox("Loading...", id="harbor-metrics", classes="data-box")
                yield MetricBox("Loading...", id="harbor-kayak", classes="status-box")
                yield MetricBox("Loading...", id="harbor-fish", classes="status-box")

            # Column 3: Fox Island
            with LocationColumn(classes="location-column", id="col-fox"):
                yield Static("FOX ISLAND (HALE PASSAGE)", classes="location-title")
                yield MetricBox("Loading...", id="fox-metrics", classes="data-box")
                yield MetricBox("Loading...", id="fox-kayak", classes="status-box")
                yield MetricBox("Loading...", id="fox-fish", classes="status-box")

        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self.update_telemetry())
        self.set_interval(360.0, lambda: self.run_worker(self.update_telemetry()))

    async def update_telemetry(self) -> None:
        data = await self.noaa.fetch_telemetry()
        
        if "error" in data:
            return

        # Get localized data from the physics engine
        zones = self.engine.get_zone_telemetry(
            data['current_knots'], 
            data['tide_feet'], 
            data['wind_knots']
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
        update_column("purdy_bridge", zones["purdy_bridge"], "purdy")
        update_column("gig_harbor", zones["gig_harbor"], "harbor")
        update_column("fox_island", zones["fox_island"], "fox")
