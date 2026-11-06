from dataclasses import dataclass

from . import proc


@dataclass
class Network:
    ssid: str
    signal: int
    security: str
    active: bool

    @property
    def secured(self) -> bool:
        return self.security not in ("", "--")


def split_terse(line: str) -> list[str]:
    """Split nmcli -t output on unescaped ':' and unescape '\\:' and '\\\\'."""
    fields, cur, i = [], [], 0
    while i < len(line):
        c = line[i]
        if c == "\\" and i + 1 < len(line):
            cur.append(line[i + 1])
            i += 2
            continue
        if c == ":":
            fields.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    fields.append("".join(cur))
    return fields


def parse_networks(out: str) -> list[Network]:
    best: dict[str, Network] = {}
    for line in out.splitlines():
        f = split_terse(line)
        if len(f) < 4 or not f[1]:
            continue
        net = Network(f[1], int(f[2] or 0), f[3], f[0] == "*")
        old = best.get(net.ssid)
        if old is None or net.active or (not old.active and net.signal > old.signal):
            best[net.ssid] = net
    return sorted(best.values(), key=lambda n: (not n.active, -n.signal))


async def interface() -> str:
    """Name of the first Wi-Fi network interface (e.g. wlp1s0), or ''."""
    _, out, _ = await proc.run("nmcli", "-t", "-f", "DEVICE,TYPE", "dev")
    for line in out.splitlines():
        dev, _, kind = line.partition(":")
        if kind == "wifi":
            return dev
    return ""


async def radio_enabled() -> bool:
    _, out, _ = await proc.run("nmcli", "radio", "wifi")
    return out.strip() == "enabled"


async def set_radio(on: bool) -> tuple[int, str, str]:
    return await proc.run("nmcli", "radio", "wifi", "on" if on else "off")


async def scan(rescan: bool = True) -> tuple[list[Network], str]:
    rc, out, err = await proc.run(
        "nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY",
        "dev", "wifi", "list", "--rescan", "yes" if rescan else "no",
        timeout=20,
    )
    return (parse_networks(out) if rc == 0 else []), err.strip()


async def connect(ssid: str, password: str | None = None) -> tuple[int, str, str]:
    if password:
        # --ask reads the passphrase from stdin, so it never shows up in `ps`.
        return await proc.run("nmcli", "--ask", "dev", "wifi", "connect", ssid,
                              timeout=40, input=password + "\n")
    return await proc.run("nmcli", "dev", "wifi", "connect", ssid, timeout=40)


def needs_password(err: str) -> bool:
    return "Secrets were required" in err or "No suitable" in err or "password" in err.lower()


async def disconnect(ssid: str) -> tuple[int, str, str]:
    return await proc.run("nmcli", "con", "down", "id", ssid)


async def forget(ssid: str) -> tuple[int, str, str]:
    return await proc.run("nmcli", "con", "delete", "id", ssid)
