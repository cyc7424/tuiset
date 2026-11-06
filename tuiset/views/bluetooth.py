from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from ..backends import bluetooth
from .common import ConfirmScreen, ListView, cell_fit, error_text, list_width, tab_is_active


class BluetoothView(ListView):
    BINDINGS = [
        Binding("s", "scan", "Scan"),
        Binding("p", "toggle_power", "Power"),
        Binding("d", "disconnect", "Disconnect"),
        Binding("x", "forget", "Forget"),
    ]

    devs: list[bluetooth.Device]
    on = True
    adapter = ""
    SCAN_SECONDS = 8

    def compose(self) -> ComposeResult:
        yield Static(id="header")
        yield OptionList(id="list")

    def on_mount(self) -> None:
        self.devs = []
        self.reload()
        self.set_interval(5, self.poll)

    def poll(self) -> None:
        if tab_is_active(self):
            self.reload()

    def focus_main(self) -> None:
        self.query_one(OptionList).focus()

    @work(exclusive=True, group="read")
    async def reload(self) -> None:
        self.on = await bluetooth.powered()
        self.adapter = await bluetooth.controller()
        self.render_header()
        self.devs = await bluetooth.devices() if self.on else []
        self.redraw()

    def render_header(self) -> None:
        self.query_one("#header", Static).update(self.status_text(f"Bluetooth ({self.adapter})" if self.adapter else "Bluetooth", self.on))

    def label(self, d: bluetooth.Device, width: int) -> Text:
        state = "connected" if d.connected else "paired" if d.paired else ""
        wide = width >= 56
        fixed = 2 + (18 if wide else 0) + (1 + len(state) if state else 0)
        name = cell_fit(d.name, max(8, min(32, width - fixed)))
        mac = f"{d.mac}  " if wide else " "
        return Text(f"{'*' if d.connected else ' '} {name}{mac}{state}".rstrip(),
                    no_wrap=True, overflow="ellipsis")

    def redraw(self) -> None:
        ol = self.query_one(OptionList)
        width = list_width(ol)
        keep = ol.highlighted
        ol.clear_options()
        ol.add_options([Option(self.label(d, width), id=d.mac) for d in self.devs])
        if self.devs:
            ol.highlighted = min(keep or 0, len(self.devs) - 1)

    def current(self) -> bluetooth.Device | None:
        i = self.query_one(OptionList).highlighted
        return self.devs[i] if i is not None and i < len(self.devs) else None

    @work(exclusive=True, group="write")
    async def action_toggle_power(self) -> None:
        rc, out, err = await bluetooth.set_power(not self.on)
        if rc or not bluetooth.ok(out):
            self.app.notify(error_text(rc, out, err), severity="error")
        self.reload()

    def action_scan(self) -> None:
        if self.on and not self.scanning:
            self.run_scan()

    @work(exclusive=True, group="scan")
    async def run_scan(self) -> None:
        await self.animate_scan(bluetooth.scan(self.SCAN_SECONDS), self.SCAN_SECONDS)
        self.reload()
        self.app.notify(f"Scan finished: {len(self.devs)} devices")

    @work(exclusive=True, group="write")
    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        d = self.devs[event.option_index]
        if d.connected:
            ok, msg = await bluetooth.disconnect(d)
        else:
            self.app.notify(f"Connecting to {d.name}…")
            ok, msg = await bluetooth.connect(d)
        self.app.notify(msg or ("OK" if ok else "failed"), severity="information" if ok else "error")
        self.reload()

    @work(exclusive=True, group="write")
    async def action_disconnect(self) -> None:
        d = self.current()
        if d and d.connected:
            ok, msg = await bluetooth.disconnect(d)
            if not ok:
                self.app.notify(msg or "failed", severity="error")
            self.reload()

    @work(exclusive=True, group="write")
    async def action_forget(self) -> None:
        d = self.current()
        if d and await self.app.push_screen_wait(ConfirmScreen(f"Forget {d.name}?")):
            ok, msg = await bluetooth.remove(d)
            self.app.notify(msg, severity="information" if ok else "error")
            self.reload()
