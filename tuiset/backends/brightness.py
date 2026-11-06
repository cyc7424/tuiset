import json

from . import proc

PANEL_PREFIXES = ("eDP", "LVDS", "DSI")


def parse(out: str) -> int | None:
    """`brightnessctl -m` -> 'dev,class,cur,pct%,max'; returns pct."""
    f = out.strip().split(",")
    if len(f) < 5:
        return None
    try:
        return int(f[3].rstrip("%"))
    except ValueError:
        return None


def parse_device(out: str) -> str:
    return out.strip().split(",")[0]


async def get() -> tuple[int | None, str, str]:
    """(percent, backlight device name, error)."""
    rc, out, err = await proc.run("brightnessctl", "-m")
    if rc:
        return None, "", err.strip()
    return parse(out), parse_device(out), err.strip()


async def display_label(device: str) -> str:
    """'eDP-1 · amdgpu_bl0' when sway reports the built-in panel, else just the device."""
    rc, out, _ = await proc.run("swaymsg", "-t", "get_outputs", "-r")
    try:
        names = [o["name"] for o in json.loads(out)] if rc == 0 else []
    except (ValueError, TypeError, KeyError):
        names = []
    panel = next((n for n in names if n.startswith(PANEL_PREFIXES)), "")
    return f"{panel} · {device}" if panel else device


async def set_percent(pct: int) -> tuple[int, str, str]:
    pct = max(1, min(100, pct))  # never go fully dark
    return await proc.run("brightnessctl", "-m", "set", f"{pct}%")
