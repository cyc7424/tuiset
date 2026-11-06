from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from ..backends import wifi
from .common import ConfirmScreen, ListView, PasswordScreen, bar, cell_fit, error_text, list_width, tab_is_active


class WifiView(ListView):
    BINDINGS = [
        Binding("s", "scan", "Scan"),
        Binding("p", "toggle_power", "Power"),
        Binding("d", "disconnect", "Disconnect"),
        Binding("x", "forget", "Forget"),
    ]

    nets: list[wifi.Network]
    enabled = True
    iface = ""

    def compose(self) -> ComposeResult:
        yield Static(id="header")
        yield OptionList(id="list")

    def on_mount(self) -> None:
        self.nets = []
        self.reload()
        self.set_interval(15, self.poll)

    def poll(self) -> None:
        if tab_is_active(self):
            self.reload()

    def focus_main(self) -> None:
        self.query_one(OptionList).focus()

    @work(exclusive=True, group="read")
    async def reload(self) -> None:
        self.enabled = await wifi.radio_enabled()
        self.iface = await wifi.interface()
        self.render_header()
        if not self.enabled:
            self.nets = []
        else:
            self.nets, err = await wifi.scan(rescan=False)
            if err:
                self.app.notify(err, severity="error")
        self.redraw()

    def render_header(self) -> None:
        self.query_one("#header", Static).update(self.status_text(f"WiFi ({self.iface})" if self.iface else "WiFi", self.enabled))

    def label(self, n: wifi.Network, width: int) -> Text:
        sec = cell_fit(n.security if n.secured else "open", 9).rstrip()
        wide = width >= 58
        fixed = 2 + 1 + 4 + 1 + len(sec) + (11 if wide else 0)
        name = cell_fit(n.ssid, max(8, min(32, width - fixed)))
        meter = f"{bar(n.signal, 10)} " if wide else ""
        return Text(f"{'*' if n.active else ' '} {name} {meter}{n.signal:>3}% {sec}",
                    no_wrap=True, overflow="ellipsis")

    def redraw(self) -> None:
        ol = self.query_one(OptionList)
        width = list_width(ol)
        keep = ol.highlighted
        ol.clear_options()
        ol.add_options([Option(self.label(n, width), id=n.ssid) for n in self.nets])
        if self.nets:
            ol.highlighted = min(keep or 0, len(self.nets) - 1)

    def action_scan(self) -> None:
        if self.enabled and not self.scanning:
            self.run_scan()

    @work(exclusive=True, group="scan")
    async def run_scan(self) -> None:
        await self.animate_scan(wifi.scan(rescan=True))
        self.reload()
        self.app.notify(f"Scan finished: {len(self.nets)} networks")

    def current(self) -> wifi.Network | None:
        i = self.query_one(OptionList).highlighted
        return self.nets[i] if i is not None and i < len(self.nets) else None

    @work(exclusive=True, group="write")
    async def action_toggle_power(self) -> None:
        rc, out, err = await wifi.set_radio(not self.enabled)
        if rc:
            self.app.notify(error_text(rc, out, err), severity="error")
        self.reload()

    @work(exclusive=True, group="write")
    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        net = self.nets[event.option_index]
        if net.active:
            return
        self.app.notify(f"Connecting to {net.ssid}…")
        rc, out, err = await wifi.connect(net.ssid)
        if rc and wifi.needs_password(out + err):
            pw = await self.app.push_screen_wait(PasswordScreen(net.ssid))
            if pw is None:
                return
            rc, out, err = await wifi.connect(net.ssid, pw)
        if rc:
            self.app.notify(error_text(rc, out, err), severity="error")
        else:
            self.app.notify(f"Connected to {net.ssid}")
        self.reload()

    @work(exclusive=True, group="write")
    async def action_disconnect(self) -> None:
        net = self.current()
        if net and net.active:
            rc, out, err = await wifi.disconnect(net.ssid)
            if rc:
                self.app.notify(error_text(rc, out, err), severity="error")
            self.reload()

    @work(exclusive=True, group="write")
    async def action_forget(self) -> None:
        net = self.current()
        if net and await self.app.push_screen_wait(ConfirmScreen(f"Forget {net.ssid}?")):
            rc, out, err = await wifi.forget(net.ssid)
            self.app.notify(error_text(rc, out, err) if rc else f"Forgot {net.ssid}",
                            severity="error" if rc else "information")
            self.reload()
