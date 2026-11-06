#!/usr/bin/env bash
# Build a single-file executable at dist/tuiset (needs uv; PyInstaller is fetched on the fly).
set -euo pipefail
cd "$(dirname "$0")"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# The package's __main__ uses a relative import, which PyInstaller can't take as a script.
printf 'from tuiset.app import main\nmain()\n' > "$tmp/entry.py"

uv run --no-project --managed-python --python 3.13 --with pyinstaller --with-editable . pyinstaller \
    --onefile --name tuiset --noconfirm --log-level WARN \
    --paths "$PWD" \
    --add-data "$PWD/tuiset/app.tcss:tuiset" \
    --collect-all textual --collect-submodules rich \
    --distpath dist --workpath "$tmp/build" --specpath "$tmp" \
    "$tmp/entry.py"

ls -lh dist/tuiset
