#!/bin/sh
set -eu

log() {
    printf '[adafruit-bonnet] %s\n' "$*"
}

# become root
if [ "$(id -u)" -ne 0 ]; then
    exec sudo "$0" "$@"
fi

HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DRIVER="$HERE/drivers/adafruit_bonnet.py"

[ -f "$DRIVER" ] || {
    echo "ERROR: missing $DRIVER"
    exit 1
}

log "finding pwnagotchi install"

PKG="$(python3 -c '
import os
import pwnagotchi
print(os.path.dirname(pwnagotchi.__file__))
')"

HW="$PKG/ui/hw"
INIT="$HW/__init__.py"
UTIL="$PKG/utils.py"
CONFIG="/etc/pwnagotchi/config.toml"

log "pwnagotchi: $PKG"

[ -f "$INIT" ] || { echo "ERROR: missing $INIT"; exit 1; }
[ -f "$UTIL" ] || { echo "ERROR: missing $UTIL"; exit 1; }

log "backing up files"

[ -e "$INIT.pre-adafruit-bonnet" ] ||
    cp "$INIT" "$INIT.pre-adafruit-bonnet"

[ -e "$UTIL.pre-adafruit-bonnet" ] ||
    cp "$UTIL" "$UTIL.pre-adafruit-bonnet"

[ ! -f "$CONFIG" ] ||
[ -e "$CONFIG.pre-adafruit-bonnet" ] ||
    cp "$CONFIG" "$CONFIG.pre-adafruit-bonnet"

log "installing driver"

install -m 0644 \
    "$DRIVER" \
    "$HW/adafruit_bonnet.py"

log "registering driver"

python3 - "$INIT" "$UTIL" <<'PY'
import sys

init_path = sys.argv[1]
util_path = sys.argv[2]

# ---------------------------------------------------------
# pwnagotchi/ui/hw/__init__.py
# ---------------------------------------------------------

with open(init_path) as f:
    src = f.read()

imp = "from pwnagotchi.ui.hw.adafruit_bonnet import AdafruitBonnet\n"

if imp not in src:
    src = imp + src

branch = """    if config['ui']['display']['type'] == 'adafruit_bonnet':
        return AdafruitBonnet(config)

"""

if "return AdafruitBonnet(config)" not in src:
    needle = "def display_for(config):\n"

    if needle not in src:
        raise SystemExit(
            "ERROR: could not find display_for() in " + init_path
        )

    src = src.replace(
        needle,
        needle + branch,
        1
    )

compile(src, init_path, "exec")

with open(init_path, "w") as f:
    f.write(src)


# ---------------------------------------------------------
# pwnagotchi/utils.py
#
# 1.8.5 normalizes/rejects display names here before
# ui/hw/__init__.py ever sees them.
# ---------------------------------------------------------

with open(util_path) as f:
    src = f.read()

if "config['ui']['display']['type'] = 'adafruit_bonnet'" not in src:

    start_marker = (
        "# the very first step is to normalize the display name"
    )

    start = src.find(start_marker)

    if start < 0:
        raise SystemExit(
            "ERROR: display normalization block not found in " +
            util_path
        )

    end = src.find("\n    return config", start)

    if end < 0:
        raise SystemExit(
            "ERROR: end of display normalization block not found"
        )

    block = src[start:end]

    pos = block.rfind("\n    else:")

    if pos < 0:
        raise SystemExit(
            "ERROR: final unsupported-display else not found"
        )

    addition = """
    elif config['ui']['display']['type'] in (
        'adafruit_bonnet',
        'adafruitbonnet',
        'adafruit_213_bonnet',
        'adafruit213bonnet'
    ):
        config['ui']['display']['type'] = 'adafruit_bonnet'
"""

    block = block[:pos] + addition + block[pos:]
    src = src[:start] + block + src[end:]

compile(src, util_path, "exec")

with open(util_path, "w") as f:
    f.write(src)

print("driver registration patched")
PY

log "configuring display"

python3 - "$CONFIG" <<'PY'
import os
import re
import sys

p = sys.argv[1]

if os.path.exists(p):
    with open(p) as f:
        src = f.read()
else:
    src = ""

def setting(src, key, value):
    pattern = r"(?m)^\s*" + re.escape(key) + r"\s*=.*$"
    line = key + " = " + value

    if re.search(pattern, src):
        return re.sub(pattern, line, src, count=1)

    if src and not src.endswith("\n"):
        src += "\n"

    return src + line + "\n"

src = setting(src, "ui.display.enabled", "true")
src = setting(src, "ui.display.type", '"adafruit_bonnet"')

# keep Pwnagotchi's canvas itself unrotated.
# adafruit_bonnet.py handles the physical panel orientation.
src = setting(src, "ui.display.rotation", "0")

with open(p, "w") as f:
    f.write(src)

print("config.toml patched")
PY

log "checking python"

python3 -m py_compile \
    "$HW/adafruit_bonnet.py" \
    "$INIT" \
    "$UTIL"

log "checking adafruit libraries"

python3 -c '
import board
import busio
import digitalio
from adafruit_epd.ssd1680 import Adafruit_SSD1680Z
print("adafruit libraries: OK")
'

log "restarting pwnagotchi"

systemctl restart pwnagotchi

sleep 3

log "done"
log "display type: adafruit_bonnet"
log "driver: $HW/adafruit_bonnet.py"

systemctl --no-pager --full status pwnagotchi | head -20 || true
