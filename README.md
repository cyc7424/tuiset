# tuiset

A small terminal control panel for a Linux laptop running sway: WiFi, Bluetooth, screen brightness and
volume in one [Textual](https://textual.textualize.io/) TUI. It does not talk to the hardware itself; it
wraps the usual command-line tools (`nmcli`, `bluetoothctl`, `brightnessctl`, `pulsemixer`, `pactl`).

> **Disclaimer.** This is a personal hobby project that I wrote for my own machine. It is provided
> **as is, with no warranty of any kind**, and I take **no responsibility** for anything that happens when
> you use it. It runs commands that change system state (turning radios on and off, disconnecting from
> networks, deleting saved WiFi profiles, removing paired Bluetooth devices, changing brightness, volume and
> default audio devices). Read the code first and use it at your own risk.

## Tested environment

Everything below is what I actually run it on. Anything else may or may not work.

| | |
|---|---|
| OS | Debian GNU/Linux 13 (trixie), kernel 6.12, x86_64 |
| Hardware | AMD laptop with an internal panel (`amdgpu_bl0` backlight), one WiFi interface (`wlp1s0`), one Bluetooth adapter (`hci0`) |
| Compositor | sway 1.10.1 (Wayland) |
| Terminal | `xterm-256color`-compatible, UTF-8 |
| Python | 3.13.5 (the project asks for 3.11+; only 3.13 was tried) |
| Textual | 8.2.8 (`pyproject.toml` asks for `>= 0.80`; only this version was tried) |
| NetworkManager (`nmcli`) | 1.52.1 |
| BlueZ (`bluetoothctl`) | 5.82 |
| `brightnessctl` | 0.5 |
| `pulsemixer` | 1.5.1 |
| Audio server | PipeWire 1.4.2 with its PulseAudio compatibility layer (`pactl` 17.0) |

### What has and has not been exercised

- Not supported or not tried: external monitors (brightness only controls the backlight device), several
  WiFi or Bluetooth adapters (the first one is shown), plain PulseAudio without PipeWire, other
  distributions, other Wayland compositors or X11 (it may run, but is untested).

## Install and run

Either way, these command-line tools must be on `PATH`; tuiset only calls them.

| Tool | Used for |
|---|---|
| `nmcli` | WiFi |
| `bluetoothctl` | Bluetooth |
| `brightnessctl` | Brightness |
| `pulsemixer` | Volume and mute |
| `pactl` | Choosing the default output/input device |
| `swaymsg` | Optional: shows the built-in display name next to the backlight |

### Option 1: single-file binary

Nothing else to install, no Python needed. Download `tuiset` from the
[Releases](../../releases) page, make it executable and run it:

    chmod +x tuiset
    mv tuiset ~/.local/bin/          # optional: put it on your PATH
    tuiset

To build it yourself instead: `./build.sh` (needs uv and binutils), which writes `dist/tuiset`.

The binary bundles Python and Textual, but not the tools above. It is built against the build machine's
glibc, so run it on the same or a newer distribution (x86_64 only). Startup takes a moment longer because
it unpacks itself on every launch.

### Option 2: from source

Needs Python 3.11+ and [uv](https://docs.astral.sh/uv/) (or pip).

    uv venv && uv pip install -e '.[dev]'
    .venv/bin/tuiset                 # or: .venv/bin/python -m tuiset
    .venv/bin/pytest                 # run the tests

## Keys

| Key | Action |
|---|---|
| `1`-`4` | Switch tab (WiFi, Bluetooth, Brightness, Volume) |
| `[` / `]` | Previous / next tab |
| `↑` `↓` or `j` `k` | Move in a list |
| `←` `→` or `h` `l` | Adjust brightness or volume (hold `Shift` on the brightness tab for 1% steps) |
| `Enter` | WiFi / Bluetooth: connect (disconnects a connected Bluetooth device). Volume: set as default device |
| `s` | WiFi / Bluetooth: scan |
| `p` | WiFi / Bluetooth: power on/off |
| `d` | WiFi / Bluetooth: disconnect |
| `x` | WiFi / Bluetooth: forget (asks for confirmation) |
| `m` | Volume: mute |
| `q` | Quit |

Lists refresh by themselves while their tab is visible. Rows adapt to the window width.

## Notes

- WiFi passwords are passed to `nmcli` on standard input (`--ask`), not as a command-line argument.

## License

[MIT](LICENSE)
