from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Static

from ..backends import brightness
from .common import bar, error_text, tab_is_active


class BrightnessView(Vertical):
    can_focus = True
    BINDINGS = [
        Binding("left,down,h,j", "adjust(-5)", "Dim"),
        Binding("right,up,l,k", "adjust(5)", "Brighten"),
        Binding("shift+left,H", "adjust(-1)", "-1", show=False),
        Binding("shift+right,L", "adjust(1)", "+1", show=False),
    ]

    pct: int | None = None
    device = ""
    label = ""

    def compose(self) -> ComposeResult:
        yield Static(id="header")
        yield Static(id="display")

    def on_mount(self) -> None:
        self.reload()
        self.set_interval(2, self.poll)

    def on_resize(self) -> None:
        self.render_bar()

    def poll(self) -> None:
        if tab_is_active(self):
            self.reload()

    def focus_main(self) -> None:
        self.focus()

    def render_bar(self) -> None:
        width = max(5, min(40, self.size.width - 6))
        text = "brightness unavailable" if self.pct is None else f"{bar(self.pct, width)} {self.pct:>3}%"
        self.query_one("#display", Static).update(text)

    @work(exclusive=True, group="read")
    async def reload(self) -> None:
        self.pct, device, err = await brightness.get()
        if self.pct is None and err:
            self.app.notify(err, severity="error")
        if device != self.device:
            self.device = device
            self.label = await brightness.display_label(device) if device else ""
        self.query_one("#header", Static).update(
            f"Brightness ({self.label})" if self.label else "Brightness")
        self.render_bar()

    def action_adjust(self, delta: int) -> None:
        if self.pct is None:
            return
        self.pct = max(1, min(100, self.pct + delta))
        self.render_bar()
        self.apply(self.pct)

    @work(exclusive=True, group="write")
    async def apply(self, pct: int) -> None:
        rc, out, err = await brightness.set_percent(pct)
        if rc:
            self.app.notify(error_text(rc, out, err), severity="error")
