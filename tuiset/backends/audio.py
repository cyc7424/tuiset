import re
from dataclasses import dataclass

from . import proc

_LINE = re.compile(
    r"(?P<kind>Sink|Source):\s+ID: (?P<id>\S+), Name: (?P<name>.*), Mute: (?P<mute>\d), "
    r"Channels: \d+, Volumes: \[(?P<vols>.*?)\](?P<default>, Default)?\s*$"
)


@dataclass
class Dev:
    id: str
    kind: str  # "Sink" | "Source"
    name: str
    volume: int
    muted: bool
    default: bool


def parse(out: str) -> list[Dev]:
    devs = []
    for line in out.splitlines():
        m = _LINE.match(line.strip())
        if not m:
            continue
        vols = [int(v) for v in re.findall(r"(\d+)%", m["vols"])]
        devs.append(Dev(m["id"], m["kind"], m["name"], round(sum(vols) / len(vols)) if vols else 0,
                        m["mute"] == "1", bool(m["default"])))
    return devs


async def devices() -> tuple[list[Dev], str]:
    (rc1, sinks, err1), (rc2, sources, _) = (
        await proc.run("pulsemixer", "--list-sinks"),
        await proc.run("pulsemixer", "--list-sources"),
    )
    err = err1.strip() if rc1 else ""
    sources = [d for d in parse(sources) if not d.name.startswith("Monitor of ")]
    return parse(sinks) + sources, err


async def set_default(dev: Dev) -> tuple[int, str, str]:
    # pulsemixer can't change defaults; pactl accepts the same numeric index as the ID suffix.
    verb = "set-default-sink" if dev.kind == "Sink" else "set-default-source"
    return await proc.run("pactl", verb, dev.id.rsplit("-", 1)[-1])


async def set_volume(dev_id: str, pct: int) -> tuple[int, str, str]:
    return await proc.run("pulsemixer", "--id", dev_id, "--set-volume", str(max(0, min(150, pct))))


async def toggle_mute(dev_id: str) -> tuple[int, str, str]:
    return await proc.run("pulsemixer", "--id", dev_id, "--toggle-mute")
