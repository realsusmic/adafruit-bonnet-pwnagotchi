# hi
# susmic here
# if you are wondering why we bypassed the circutpython display driver, it's because normally there would be a 8px artifact at the top, but this way we bypass it
# txx

import logging
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.hw.base import DisplayImpl

try:
    import time as _gdey_time
    from adafruit_epd.ssd1680 import Adafruit_SSD1680Z as _SSD1680Z_Base

    class GDEY0213B74Fixed(_SSD1680Z_Base):

        def __init__(self, *args, **kwargs):
            super(GDEY0213B74Fixed, self).__init__(*args, **kwargs)

            # THIS IS A MONO PANEL.
            #
            # Adafruit's Arduino GDEY0213B74 class maps both logical
            # colours to the same framebuffer. Do the equivalent here.
            self.set_black_buffer(0, True)
            self.set_color_buffer(0, True)

        def _gdey_set_window(self):
            # Good Display / GxEPD2 native RAM geometry:
            #
            # physical panel = 122 x 250
            # RAM X = 16 byte columns = 128 source bits
            # RAM Y = 250 gates
            #
            # X increases, Y increases.
            self.command(0x11, bytearray([0x03]))

            # RAM X: byte 0 through byte 15
            self.command(
                0x44,
                bytearray([0x00, 0x0F])
            )

            # RAM Y: row 0 through row 249 (0x00F9)
            self.command(
                0x45,
                bytearray([
                    0x00, 0x00,
                    0xF9, 0x00
                ])
            )

            # RAM counters at the true origin.
            # NO x+1.
            self.command(0x4E, bytearray([0x00]))
            self.command(0x4F, bytearray([0x00, 0x00]))

        def power_up(self):
            self.hardware_reset()
            self.busy_wait()

            # Software reset
            self.command(0x12)
            self.busy_wait()

            # 250 gate outputs => last gate address is 249.
            self.command(
                0x01,
                bytearray([0xF9, 0x00, 0x00])
            )

            # Good Display's B74 init starts in Y-decrement mode,
            # then _gdey_set_window() changes to normal 0x03.
            self.command(0x11, bytearray([0x01]))

            # Border waveform
            self.command(0x3C, bytearray([0x05]))

            # CRITICAL B74-SPECIFIC SOURCE MAPPING.
            #
            # SSD1680 datasheet:
            #   B7 = 0 -> sources S0..S175
            #   B7 = 1 -> sources S8..S167
            #
            # Good Display/GxEPD2 explicitly uses 00 80 on GDEY0213B74.
            self.command(
                0x21,
                bytearray([0x00, 0x80])
            )

            # Use the controller's internal temperature sensor.
            # Also present in Good Display/GxEPD2 B74 init.
            self.command(0x18, bytearray([0x80]))

            self._gdey_set_window()
            self.busy_wait()

        def set_ram_address(self, x, y):
            # Ignore the ancient base driver's x+1 behavior completely.
            #
            # Full-frame Pwnagotchi writes always begin at native RAM origin.
            self.command(0x4E, bytearray([0x00]))
            self.command(0x4F, bytearray([0x00, 0x00]))

        def write_ram(self, index):
            # This physical panel is monochrome.
            #
            # Only BW RAM 0x24 is used by this driver.
            # Never let Adafruit_EPD.display() treat buffer #2 as red RAM.
            if index != 0:
                raise RuntimeError('GDEY0213B74 mono driver has no second display plane')
            return self.command(0x24, end=False)

        def display(self):
            # DO NOT call Adafruit_EPD.display().
            #
            # adafruit-circuitpython-epd 2.13.0 unconditionally writes its
            # allocated second framebuffer to SSD1680 command 0x26.
            # That path is for the generic tri-colour abstraction and is
            # not what we want on this GDEY0213B74 mono panel.

            if self.sram:
                raise RuntimeError('GDEY0213B74 v4 expects sramcs_pin=None')

            self.power_up()

            # Reassert window + counters immediately before the RAM transfer.
            self._gdey_set_window()

            # Begin BLACK/WHITE RAM write, leaving CS asserted.
            self.command(0x24, end=False)

            while not self.spi_device.try_lock():
                _gdey_time.sleep(0.01)

            try:
                self._dc.value = True

                # Exactly 4000 bytes:
                # 16 bytes/row * 250 rows.
                self._spi_transfer(self._buffer1)

                self._cs.value = True
            finally:
                self.spi_device.unlock()

            _gdey_time.sleep(0.002)

            self.update()

        def update(self):
            # Good Display/GxEPD2 normal full refresh.
            self.command(0x22, bytearray([0xF7]))
            self.command(0x20)
            self.busy_wait()

except ImportError:
    GDEY0213B74Fixed = None

class AdafruitBonnet(DisplayImpl):
    def __init__(self, config):
        super(AdafruitBonnet, self).__init__(config, 'adafruit_bonnet')
        self._display = None

    def layout(self):
        fonts.setup(10, 9, 10, 35, 25, 9)
        self._layout['width']       = 250
        self._layout['height']      = 122
        self._layout['face']        = (0, 40)
        self._layout['name']        = (5, 20)
        self._layout['channel']     = (0, 0)
        self._layout['aps']         = (28, 0)
        self._layout['uptime']      = (185, 0)
        self._layout['line1']       = [0, 14, 250, 14]
        self._layout['line2']       = [0, 108, 250, 108]
        self._layout['friend_face'] = (0, 92)
        self._layout['friend_name'] = (40, 94)
        self._layout['shakes']      = (0, 109)
        self._layout['mode']        = (225, 109)
        self._layout['status'] = {'pos': (125, 20), 'font': fonts.status_font(fonts.Medium), 'max': 20}
        return self._layout

    def initialize(self):
        import board, busio, digitalio
        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        ecs, dc, rst, busy = (digitalio.DigitalInOut(p) for p in (board.CE0, board.D22, board.D27, board.D17))
        variant = str(self.config.get('adafruit_variant', 'auto')).lower()
        display, errs = None, []
        if variant in ('auto', 'z'):
            try:
                from adafruit_epd.ssd1680 import Adafruit_SSD1680Z
                display = GDEY0213B74Fixed(122, 250, spi, cs_pin=ecs, dc_pin=dc, sramcs_pin=None, rst_pin=rst, busy_pin=busy)
                display.rotation = 1
                logging.info("[adafruit_bonnet] initialized as SSD1680Z")
            except Exception as e:
                errs.append(f"SSD1680Z: {e}")
        if display is None and variant in ('auto', 'legacy'):
            try:
                try: from adafruit_epd.ssd1680 import Adafruit_SSD1680_Legacy as L
                except ImportError: from adafruit_epd.ssd1680 import Adafruit_SSD1680 as L
                display = L(122, 250, spi, cs_pin=ecs, dc_pin=dc, sramcs_pin=None, rst_pin=rst, busy_pin=busy)
                display.rotation = 2
                logging.info("[adafruit_bonnet] initialized as Legacy")
            except Exception as e:
                errs.append(f"Legacy: {e}")
        if display is None:
            raise RuntimeError("[adafruit_bonnet] init failed: " + "; ".join(errs))
        self._display = display

    def render(self, canvas):
        if self._display is None: return
        try:
            canvas = canvas.convert('L')
            self._display.image(canvas)
            self._display.display()
        except Exception as e:
            logging.error(f"[adafruit_bonnet] render: {e}")

    def clear(self):
        if self._display is None: return
        try: self._display.fill(0xFF); self._display.display()
        except Exception as e: logging.error(f"[adafruit_bonnet] clear: {e}")
