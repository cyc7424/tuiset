from tuiset.backends import audio, bluetooth, brightness, wifi


def test_split_terse_escapes():
    assert wifi.split_terse(r"*:My\:Net:80:WPA2") == ["*", "My:Net", "80", "WPA2"]


def test_wifi_parse_dedup_and_order():
    out = ":Cafe:40:WPA2\n*:Home:60:WPA2\n:Cafe:70:WPA2\n:Open:30:\n::10:WPA2\n"
    nets = wifi.parse_networks(out)
    assert [n.ssid for n in nets] == ["Home", "Cafe", "Open"]
    assert nets[1].signal == 70
    assert nets[0].active and not nets[2].secured


def test_bluetooth_parse():
    devs = bluetooth.parse_devices("Device AA:BB:CC:DD:EE:FF My Buds\nDevice 11:22:33:44:55:66 Phone X\n")
    assert [(d.mac, d.name) for d in devs] == [("AA:BB:CC:DD:EE:FF", "My Buds"), ("11:22:33:44:55:66", "Phone X")]
    info = bluetooth.parse_info("Device AA\n\tPaired: yes\n\tConnected: no\n")
    assert info == {"Paired": "yes", "Connected": "no"}


def test_brightness_parse():
    assert brightness.parse("amdgpu_bl0,backlight,105,41%,255\n") == 41
    assert brightness.parse("garbage") is None


def test_audio_parse():
    out = ("Sink:\t\t ID: sink-57, Name: Speaker, Foo, Mute: 1, Channels: 2, Volumes: ['30%', '50%'], Default\n"
           "Source:\t\t ID: source-1, Name: Mic, Mute: 0, Channels: 1, Volumes: ['100%']\n")
    a, b = audio.parse(out)
    assert (a.id, a.name, a.volume, a.muted, a.default) == ("sink-57", "Speaker, Foo", 40, True, True)
    assert (b.kind, b.volume, b.default) == ("Source", 100, False)


def test_brightness_parse_device():
    assert brightness.parse_device("amdgpu_bl0,backlight,105,41%,255\n") == "amdgpu_bl0"


async def test_bluetooth_devices_uses_filters(monkeypatch):
    from tuiset.backends import proc

    calls = []

    async def fake_run(*cmd, timeout=10.0):
        calls.append(cmd)
        if cmd[1:] == ("--version",):
            return 0, "bluetoothctl: 5.82\n", ""
        if cmd[1:] == ("devices",):
            return 0, "Device AA Buds\nDevice BB Phone\nDevice CC Old\n", ""
        if cmd[1:] == ("devices", "Paired"):
            return 0, "Device AA Buds\nDevice BB Phone\n", ""
        if cmd[1:] == ("devices", "Connected"):
            return 0, "Device BB Phone\n", ""
        raise AssertionError(cmd)

    monkeypatch.setattr(proc, "run", fake_run)
    monkeypatch.setattr(bluetooth, "_filters", None)
    devs = await bluetooth.devices()
    assert [(d.name, d.paired, d.connected) for d in devs] == [
        ("Phone", True, True), ("Buds", True, False), ("Old", False, False)]
    assert not any(c[1] == "info" for c in calls)


async def test_proc_input_goes_to_stdin():
    from tuiset.backends import proc

    rc, out, _ = await proc.run("cat", input="hunter2\n")
    assert (rc, out) == (0, "hunter2\n")


async def test_wifi_password_not_in_argv(monkeypatch):
    from tuiset.backends import proc

    seen = {}

    async def fake_run(*cmd, timeout=10.0, input=None):
        seen["cmd"], seen["input"] = cmd, input
        return 0, "", ""

    monkeypatch.setattr(proc, "run", fake_run)
    await wifi.connect("Home", "hunter2")
    assert "hunter2" not in " ".join(seen["cmd"]) and "--ask" in seen["cmd"]
    assert seen["input"] == "hunter2\n"
    await wifi.connect("Home")
    assert "--ask" not in seen["cmd"] and seen["input"] is None


async def test_audio_set_default_uses_pactl(monkeypatch):
    from tuiset.backends import proc

    seen = {}

    async def fake_run(*cmd, timeout=10.0, input=None):
        seen["cmd"] = cmd
        return 0, "", ""

    monkeypatch.setattr(proc, "run", fake_run)
    await audio.set_default(audio.Dev("source-59", "Source", "Mic", 100, False, False))
    assert seen["cmd"] == ("pactl", "set-default-source", "59")
