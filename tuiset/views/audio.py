from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from ..backends import audio
from .common import ListView, bar, cell_fit, error_text, list_width, tab_is_active


class AudioView(ListView):
    BINDINGS = [
        Binding("left,h", "adjust(-5)", "Vol-"),
        Binding("right,l", "adjust(5)", "Vol+"),
        Binding("m", "mute", "Mute"),
    ]

    devs: list[audio.Dev]

    def compose(self) -> ComposeResult:
        yield Static(id="header")
        yield OptionList(id="list")

    def on_mount(self) -> None:
        self.devs = []
        self.reload()
        self.set_interval(2, self.poll)

    def poll(self) -> None:
        if tab_is_active(self):
            self.reload()

    def focus_main(self) -> None:
        self.query_one(OptionList).focus()

    def label(self, d: audio.Dev, width: int) -> Text:
        kind = "OUT" if d.kind == "Sink" else "IN "
        star = "*" if d.default else " "
        vol = f"{d.volume:>3}%" + (" muted" if d.muted else "")
        bar_w = 20 if width >= 80 else 10 if width >= 64 else 0
        fixed = 6 + 1 + 10 + (bar_w + 1 if bar_w else 0)
        name = cell_fit(d.name, max(8, min(36, width - fixed)))
        meter = f"{bar(d.volume, bar_w, 150)} " if bar_w else ""
        return Text(f"{star} {kind} {name} {meter}{vol}", no_wrap=True, overflow="ellipsis")

    def render_header(self) -> None:
        out = next((d for d in self.devs if d.kind == "Sink" and d.default), None)
        state = "" if out is None else "muted" if out.muted else f"{out.volume}%"
        self.query_one("#header", Static).update(f"Volume: {state}" if state else "Volume")

    def redraw(self) -> None:
        self.render_header()
        ol = self.query_one(OptionList)
        width = list_width(ol)
        keep = ol.highlighted
        ol.clear_options()
        ol.add_options([Option(self.label(d, width), id=d.id) for d in self.devs])
        if self.devs:
            ol.highlighted = min(keep or 0, len(self.devs) - 1)

    @work(exclusive=True, group="read")
    async def reload(self) -> None:
        self.devs, err = await audio.devices()
        if not self.devs and err:
            self.app.notify(err, severity="error")
        self.redraw()

    def current(self) -> audio.Dev | None:
        i = self.query_one(OptionList).highlighted
        return self.devs[i] if i is not None and i < len(self.devs) else None

    def action_adjust(self, delta: int) -> None:
        d = self.current()
        if d is None:
            return
        d.volume = max(0, min(150, d.volume + delta))
        self.redraw()
        self.write(audio.set_volume(d.id, d.volume))

    @work(exclusive=True, group="default")
    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        d = self.devs[event.option_index]
        if d.default:
            return
        rc, out, err = await audio.set_default(d)
        if rc:
            self.app.notify(error_text(rc, out, err), severity="error")
        else:
            self.app.notify(f"Default {'output' if d.kind == 'Sink' else 'input'}: {d.name}")
        self.reload()

    def action_mute(self) -> None:
        d = self.current()
        if d is None:
            return
        d.muted = not d.muted
        self.redraw()
        self.write(audio.toggle_mute(d.id))

    @work(exclusive=True, group="write")
    async def write(self, coro) -> None:
        rc, out, err = await coro
        if rc:
            self.app.notify(error_text(rc, out, err), severity="error")
