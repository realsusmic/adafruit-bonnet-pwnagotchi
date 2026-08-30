# [Adafruit Bonnet](https://www.adafruit.com/product/4687) display driver
# Deps
This driver needs some dependincies to properly function. You should probably already have Python installed, if not, run:
```bash
sudo apt update
sudo apt install -y \
    python3-pip \
    python3-dev \
    libgpiod2
```
.. to install it.
If Python is already installed, install the driver depenincies via pip:
```bash
sudo python3 -m pip install \
    "adafruit-circuitpython-epd==2.13.0" \
    "Adafruit-Blinka"
    "Pillow"
```
This driver also needs SPI, enable it in raspi-config:
```bash
sudo raspi-config nonint do_spi 0

# output should be: 
# /dev/spidev0.0
# /dev/spidev0.1
```
Do NOT install the new version of adafruit-circuitpython-ssd1680, if you have installed it: run this command:
```bash
python3 -m pip uninstall adafruit-circuitpython-epd
python3 -m pip install "adafruit-circuitpython-epd==2.13.0"
```
If you want to check if everything works before you install it,
```python
python3 - <<'PY'
import board
import busio
import digitalio
import adafruit_framebuf

from adafruit_epd.ssd1680 import (
    Adafruit_SSD1680,
    Adafruit_SSD1680Z,
)

print("board:", board)
print("busio:", busio)
print("digitalio:", digitalio)
print("framebuf:", adafruit_framebuf)
print("SSD1680:", Adafruit_SSD1680)
print("SSD1680Z:", Adafruit_SSD1680Z)
print("all display deps are alive")
PY
```

# The driver
(With SSH) Copy the driver from [here](https://raw.githubusercontent.com/realsusmic/adafruit-bonnet-pwnagotchi/refs/heads/main/adafruit_bonnet.py), open NANO in SSH:
```bash
# for jayofelony
sudo nano /home/pi/.pwn/lib/python3.11/site-packages/pwnagotchi/ui/hw/adafruit_bonnet.py
# for evilsocket
# sudo nano /usr/local/lib/python3.7/dist-packages/pwnagotchi/ui/hw/adafruit_bonnet.py
```
After pasting the driver you copied into NANO, save it with:

```text
CTRL+O
ENTER
CTRL+X
```

## Registering the driver

Pwnagotchi will not automatically detect a new display driver just because the file exists. You also need to register `adafruit_bonnet` as a valid display type.

### Jayofelony

Open:

```bash
sudo nano /home/pi/.pwn/lib/python3.11/site-packages/pwnagotchi/ui/hw/__init__.py
```

Find:

```python
def display_for(config):
```

Inside that function, add:

```python
elif config['ui']['display']['type'] == 'adafruit_bonnet':
    from pwnagotchi.ui.hw.adafruit_bonnet import AdafruitBonnet
    return AdafruitBonnet(config)
```

Make sure the indentation matches the other `elif` entries.

Save with:

```text
CTRL+O
ENTER
CTRL+X
```

Now open:

```bash
sudo nano /home/pi/.pwn/lib/python3.11/site-packages/pwnagotchi/utils.py
```

Find the section that validates or normalizes:

```python
config['ui']['display']['type']
```

Before the final unsupported-display `else:`, add:

```python
elif config['ui']['display']['type'] in ('adafruit_bonnet', 'adafruit-bonnet'):
    config['ui']['display']['type'] = 'adafruit_bonnet'
```

This is important because otherwise Jayofelony may replace the unknown display type with `dummydisplay`.

---

### Evilsocket

Open:

```bash
sudo nano /usr/local/lib/python3.7/dist-packages/pwnagotchi/ui/hw/__init__.py
```

Near the other display imports, add:

```python
from pwnagotchi.ui.hw.adafruit_bonnet import AdafruitBonnet
```

Then find:

```python
def display_for(config):
```

and add:

```python
elif config['ui']['display']['type'] == 'adafruit_bonnet':
    return AdafruitBonnet(config)
```

Save and exit.

Now open:

```bash
sudo nano /usr/local/lib/python3.7/dist-packages/pwnagotchi/utils.py
```

In the display type validation section, before the final unsupported-display `else:`, add:

```python
elif config['ui']['display']['type'] in ('adafruit_bonnet', 'adafruit-bonnet'):
    config['ui']['display']['type'] = 'adafruit_bonnet'
```

Save and exit.

## Configure Pwnagotchi

Open:

```bash
sudo nano /etc/pwnagotchi/config.toml
```

Set the display configuration to:

```toml
ui.display.enabled = true
ui.display.type = "adafruit_bonnet"
ui.display.rotation = 0
```

If those options already exist, edit the existing values instead of adding duplicates.

## Check the driver for syntax errors

### Jayofelony

```bash
/home/pi/.pwn/bin/python -m py_compile \
/home/pi/.pwn/lib/python3.11/site-packages/pwnagotchi/ui/hw/adafruit_bonnet.py
```

### Evilsocket

```bash
python3 -m py_compile \
/usr/local/lib/python3.7/dist-packages/pwnagotchi/ui/hw/adafruit_bonnet.py
```

If the command prints nothing, the Python syntax is valid.

## Restart Pwnagotchi

```bash
sudo systemctl restart pwnagotchi
```

Then check the logs:

```bash
sudo journalctl -u pwnagotchi -n 100 --no-pager
```

A successful initialization should contain something similar to:

```text
[adafruit_bonnet] initialized as SSD1680Z
```

If it instead says:

```text
using dummy display
```

then the display type was not correctly registered in `utils.py`.

If it says:

```text
unsupported display type
```

then the display type was not correctly registered in the Pwnagotchi display loader.

If it fails to import:

```text
Adafruit_SSD1680Z
```

verify that the correct EPD version is installed:

```bash
python3 -m pip show adafruit-circuitpython-epd
```

The version should be:

```text
2.13.0
```

For Jayofelony, check using its Python environment instead:

```bash
/home/pi/.pwn/bin/python -m pip show adafruit-circuitpython-epd
```

## Done

after it restarts and does it's thing, the eink should shiow the pwnagotchi ui

