import asyncio
from dataclasses import dataclass
from pathlib import Path

from . import proc


@dataclass
class Device:
    mac: str
    name: str
    paired: bool = False
    connected: bool = False


def parse_devices(out: str) -> list[Device]:
    devs = []
    for line in out.splitlines():
        parts = line.split(" ", 2)
        if len(parts) == 3 and parts[0] == "Device":
            devs.append(Device(parts[1], parts[2]))
    return devs


def parse_info(out: str) -> dict[str, str]:
    info = {}
    for line in out.splitlines()[1:]:
        key, sep, val = line.strip().partition(": ")
        if sep:
            info[key] = val
    return info


def ok(out: str) -> bool:
    return "Failed" not in out and "not available" not in out


async def powered() -> bool:
    _, out, _ = await proc.run("bluetoothctl", "show")
    return parse_info("\n" + out).get("Powered") == "yes"


async def controller() -> str:
    """Adapter name (e.g. hci0); falls back to its address when ambiguous."""
    adapters = sorted(p.name for p in Path("/sys/class/bluetooth").glob("hci*") if p.name[3:].isdigit())
    if len(adapters) == 1:
        return adapters[0]
    _, out, _ = await proc.run("bluetoothctl", "show")
    first = out.splitlines()[0].split() if out else []
    return first[1] if len(first) > 1 and first[0] == "Controller" else ""


async def set_power(on: bool) -> tuple[int, str, str]:
    return await proc.run("bluetoothctl", "power", "on" if on else "off")


async def devices() -> list[Device]:
    rc, out, _ = await proc.run("bluetoothctl", "devices")
    devs = parse_devices(out)
    if rc == 0 and await _has_filters():
        (_, paired, _), (_, connected, _) = await asyncio.gather(
            proc.run("bluetoothctl", "devices", "Paired"),
            proc.run("bluetoothctl", "devices", "Connected"),
        )
        paired_macs = {d.mac for d in parse_devices(paired)}
        connected_macs = {d.mac for d in parse_devices(connected)}
        for d in devs:
            d.paired = d.mac in paired_macs
            d.connected = d.mac in connected_macs
        return _sorted(devs)

    async def fill(d: Device) -> None:
        _, info, _ = await proc.run("bluetoothctl", "info", d.mac)
        i = parse_info(info)
        d.paired = i.get("Paired") == "yes"
        d.connected = i.get("Connected") == "yes"

    await asyncio.gather(*(fill(d) for d in devs))
    return _sorted(devs)


def _sorted(devs: list[Device]) -> list[Device]:
    return sorted(devs, key=lambda d: (not d.connected, not d.paired, d.name.lower()))


_filters: bool | None = None


async def _has_filters() -> bool:
    """`devices Paired|Connected` needs bluez >= 5.65; older ones ignore the argument."""
    global _filters
    if _filters is None:
        _, out, _ = await proc.run("bluetoothctl", "--version")
        try:
            major, minor = out.split()[-1].split(".")[:2]
            _filters = (int(major), int(minor)) >= (5, 65)
        except (ValueError, IndexError):
            _filters = False
    return _filters


async def scan(seconds: int = 8) -> None:
    await proc.run("bluetoothctl", "--timeout", str(seconds), "scan", "on", timeout=seconds + 5)


async def connect(d: Device) -> tuple[bool, str]:
    if not d.paired:
        _, out, _ = await proc.run("bluetoothctl", "pair", d.mac, timeout=30)
        if not ok(out):
            return False, out.strip().splitlines()[-1] if out.strip() else "pair failed"
        await proc.run("bluetoothctl", "trust", d.mac)
    _, out, err = await proc.run("bluetoothctl", "connect", d.mac, timeout=30)
    msg = (out + err).strip()
    return ok(out) and "successful" in out, msg.splitlines()[-1] if msg else ""


async def disconnect(d: Device) -> tuple[bool, str]:
    _, out, _ = await proc.run("bluetoothctl", "disconnect", d.mac)
    return "Successful" in out, out.strip().splitlines()[-1] if out.strip() else ""


async def remove(d: Device) -> tuple[bool, str]:
    _, out, _ = await proc.run("bluetoothctl", "remove", d.mac)
    return "removed" in out, out.strip().splitlines()[-1] if out.strip() else ""
