import asyncio
import time

from rich.cells import cell_len, set_cell_size
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, OptionList, TabbedContent


def bar(pct: int, width: int = 30, maximum: int = 100) -> str:
    filled = round(width * max(0, min(pct, maximum)) / maximum)
    return "█" * filled + "░" * (width - filled)


def tab_is_active(view) -> bool:
    return view.screen.query_one(TabbedContent).active == view.parent.id


def cell_fit(s: str, width: int) -> str:
    """Pad or truncate (with …) to exactly `width` terminal cells; CJK-safe."""
    if cell_len(s) > width:
        s = set_cell_size(s, max(width - 1, 0)) + "…"
    return set_cell_size(s, width)


def list_width(ol: OptionList) -> int:
    return max(ol.scrollable_content_region.width - 1, 0)


def error_text(rc: int, out: str, err: str) -> str:
    msg = (err or out).strip()
    return msg.splitlines()[-1] if msg else f"exit code {rc}"


class PasswordScreen(ModalScreen[str | None]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, ssid: str) -> None:
        super().__init__()
        self.ssid = ssid

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(f"Password for {self.ssid}")
            yield Input(password=True, id="pw")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value or None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ListView(Vertical):
    """Base for views built around one OptionList: adds j/k navigation."""
    BINDINGS = [
        Binding("j", "move(1)", "Down", show=False),
        Binding("k", "move(-1)", "Up", show=False),
    ]

    SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    scanning = False
    scan_left: int | None = None
    _drawn_width = -1

    def status_text(self, name: str, on: bool) -> str:
        if not on:
            return f"{name}: OFF  (press p to enable)"
        if not self.scanning:
            return f"{name}: ON"
        frame = self.SPINNER[int(time.monotonic() * 10) % len(self.SPINNER)]
        left = f" {self.scan_left}s" if self.scan_left is not None else ""
        return f"{name}: ON  {frame} Scanning…{left}"

    def render_header(self) -> None:
        raise NotImplementedError

    async def animate_scan(self, coro, seconds: int | None = None) -> None:
        """Run a scan coroutine, animating the header and refreshing the list as it goes."""
        self.scanning = True
        start = time.monotonic()
        task = asyncio.create_task(coro)
        try:
            ticks = 0
            while not task.done():
                if seconds is not None:
                    self.scan_left = max(0, round(start + seconds - time.monotonic()))
                self.render_header()
                if ticks and ticks % 15 == 0:  # ~1.5s: show results as they are found
                    self.reload()
                ticks += 1
                await asyncio.wait({task}, timeout=0.1)
        finally:
            task.cancel()
            self.scanning = False
            self.scan_left = None
            self.render_header()

    def on_resize(self) -> None:
        # Row layout depends on the list width, which settles after this event.
        self.call_after_refresh(self.relayout)

    def relayout(self) -> None:
        w = list_width(self.query_one(OptionList))
        if w != self._drawn_width:
            self._drawn_width = w
            self.redraw()

    def redraw(self) -> None:
        raise NotImplementedError

    def action_move(self, step: int) -> None:
        ol = self.query_one(OptionList)
        ol.action_cursor_down() if step > 0 else ol.action_cursor_up()


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [
        Binding("y", "answer(True)", "Yes"),
        Binding("n,escape", "answer(False)", "No"),
    ]

    def __init__(self, question: str) -> None:
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.question)
            yield Label("[b]y[/b]es / [b]n[/b]o")

    def action_answer(self, value: bool) -> None:
        self.dismiss(value)
