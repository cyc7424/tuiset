import asyncio

from textual.widgets import TabbedContent

from tuiset.app import TuiSet
from tuiset.backends import proc


async def test_tab_switching(monkeypatch):
    async def fake_run(*cmd, timeout=10.0):
        return 127, "", "missing"

    monkeypatch.setattr(proc, "run", fake_run)
    app = TuiSet()
    async with app.run_test() as pilot:
        await pilot.pause()
        tc = app.query_one(TabbedContent)
        assert tc.active == "wifi"
        await pilot.press("3")
        await pilot.pause()
        assert tc.active == "brightness"
        await pilot.press("4")
        await pilot.pause()
        assert tc.active == "audio"


async def test_step_tab_wraps(monkeypatch):
    async def fake_run(*cmd, timeout=10.0):
        return 127, "", "missing"

    monkeypatch.setattr(proc, "run", fake_run)
    app = TuiSet()
    async with app.run_test() as pilot:
        await pilot.pause()
        tc = app.query_one(TabbedContent)
        await pilot.press("[")
        await pilot.pause()
        assert tc.active == "audio"
        await pilot.press("]")
        await pilot.pause()
        assert tc.active == "wifi"


async def test_bluetooth_scan_shows_indicator(monkeypatch):
    from textual.widgets import Static

    from tuiset.backends import bluetooth

    async def fake_run(*cmd, timeout=10.0):
        return 127, "", "missing"

    async def fake_powered():
        return True

    async def fake_scan(seconds=8):
        await asyncio.sleep(0.5)

    monkeypatch.setattr(proc, "run", fake_run)
    monkeypatch.setattr(bluetooth, "powered", fake_powered)
    monkeypatch.setattr(bluetooth, "scan", fake_scan)
    app = TuiSet()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("2")
        await pilot.pause(0.1)
        await pilot.press("s")
        await pilot.pause(0.2)
        assert "Scanning" in str(app.query_one("#bluetooth #header", Static).render())
        await pilot.pause(1.0)
        assert "Scanning" not in str(app.query_one("#bluetooth #header", Static).render())


async def test_narrow_window_does_not_crash(monkeypatch):
    async def fake_run(*cmd, timeout=10.0):
        return 127, "", "missing"

    monkeypatch.setattr(proc, "run", fake_run)
    app = TuiSet()
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        for size in [(40, 12), (25, 8), (120, 30)]:
            await pilot.resize_terminal(*size)
            await pilot.pause()


async def test_wifi_scan_shows_indicator(monkeypatch):
    from textual.widgets import Static

    from tuiset.backends import wifi

    async def fake_enabled():
        return True

    async def fake_scan(rescan=True):
        if rescan:
            await asyncio.sleep(0.5)
        return [], ""

    monkeypatch.setattr(wifi, "radio_enabled", fake_enabled)
    monkeypatch.setattr(wifi, "scan", fake_scan)
    app = TuiSet()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("s")
        await pilot.pause(0.2)
        assert "Scanning" in str(app.query_one("#wifi #header", Static).render())
        await pilot.pause(1.0)
        assert "Scanning" not in str(app.query_one("#wifi #header", Static).render())
