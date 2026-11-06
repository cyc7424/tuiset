from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, TabbedContent, TabPane

from .views.audio import AudioView
from .views.bluetooth import BluetoothView
from .views.brightness import BrightnessView
from .views.wifi import WifiView

TABS = [
    ("wifi", "WiFi", WifiView),
    ("bluetooth", "Bluetooth", BluetoothView),
    ("brightness", "Brightness", BrightnessView),
    ("audio", "Volume", AudioView),
]


class TuiSet(App):
    TITLE = "tuiset"
    CSS_PATH = "app.tcss"
    BINDINGS = [
        *(Binding(str(i), f"tab('{tid}')", label, show=False) for i, (tid, label, _) in enumerate(TABS, 1)),
        Binding("]", "step_tab(1)", "Next tab", show=False),
        Binding("[", "step_tab(-1)", "Prev tab", show=False),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        with TabbedContent():
            for i, (tid, label, view) in enumerate(TABS, 1):
                with TabPane(f"{i} {label}", id=tid):
                    yield view()
        yield Footer()

    def on_mount(self) -> None:
        self.focus_active()

    def focus_active(self) -> None:
        tc = self.query_one(TabbedContent)
        pane = tc.get_pane(tc.active)
        view = pane.children[0]
        self.call_after_refresh(view.focus_main)
        view.poll()

    def action_tab(self, tid: str) -> None:
        self.query_one(TabbedContent).active = tid

    def action_step_tab(self, step: int) -> None:
        tc = self.query_one(TabbedContent)
        ids = [t[0] for t in TABS]
        tc.active = ids[(ids.index(tc.active) + step) % len(ids)]

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        self.focus_active()


def main() -> None:
    TuiSet().run()


if __name__ == "__main__":
    main()
