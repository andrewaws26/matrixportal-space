# MatrixPortal Space

Multi-animation 64x32 RGB LED matrix display with Wi-Fi phone control, built on CircuitPython.

## Hardware

### Controller: Adafruit MatrixPortal S3 (Product 5778)
- **Processor:** ESP32-S3 (dual-core Xtensa LX7 @ 240 MHz)
- **Memory:** 8 MB flash, 2 MB PSRAM, 512 KB internal SRAM
- **WiFi:** 2.4 GHz 802.11 b/g/n (no 5 GHz). ~800 KB/s throughput
- **Bluetooth:** BLE 5 in hardware, but **NOT supported in CircuitPython** — only usable via Arduino/ESP-IDF
- **USB-C:** Native USB — CircuitPython REPL, file transfer (CIRCUITPY drive), HID capable
- **Built-in peripherals:**
  - 2 user buttons: `board.BUTTON_UP` (GPIO 6), `board.BUTTON_DOWN` (GPIO 7)
  - 1 NeoPixel: `board.NEOPIXEL` (GPIO 4)
  - 1 red LED: `board.LED` (GPIO 13)
  - LIS3DH accelerometer on I2C at address **0x19** (not the default 0x18 — must override in code)
  - STEMMA QT I2C connector (3.3V, with pullups)
  - 3-pin JST with A0 analog input
  - 6 user GPIO on bottom edge (A0–A4 + extras), support analog/digital/PWM/SPI/I2S
- **HUB75 output:** 2x10 socket with level shifters (3.3V→5V). Supports 16x32 up to 64x64 panels
  - Address E solder jumper for 64x64 (1/32 scan) panels — not needed for our 64x32
  - Chaining supported via `chain_across`, `tile_down`, `serpentine` params
- **Power:** 5V via USB-C. 3V regulator: 500 mA. M3 screw terminals for external 5V matrix power
- **Firmware:** CircuitPython 10.1.4, TinyUF2 bootloader (0.33.0+ required for CP 10+)

### Display: Waveshare RGB-Matrix-P4-64x32 (SKU 22101)
- **Resolution:** 64x32 pixels (2048 RGB LEDs), 4mm pitch
- **Physical size:** 256mm x 128mm (~10" x 5")
- **Interface:** HUB75 (standard, not HUB75E). 1/16 scan rate (4 address lines: A, B, C, D)
- **Power:** 5V DC, up to 4A at full white (20W max). Typical ~2A with mixed content
- **Color depth:** Depends on controller — we use `bit_depth=6` for up to 262K colors
- **Viewing angle:** ≥160°
- **Chaining:** Output IDC header for daisy-chain. Practical limit with MatrixPortal S3: 2–4 panels
- **No onboard PWM** — all color modulation done by the microcontroller. Panel goes dark if not continuously driven

### Key Hardware Constraints
- USB-C alone insufficient for full-brightness white — use external 5V supply for bright displays
- `bit_depth=6` consumes ~30% CPU on a single 64x32 panel. Higher depth = smoother color but slower Python
- Each 64x32 panel: ~17 KB RAM at bit_depth=6. With doublebuffer: ~34 KB
- All GPIO are 3.3V — MatrixPortal S3 has level shifters for HUB75 but external 5V devices need shifting
- WiFi is 2.4 GHz only

## Project Structure

```
code.py              # Main application — all animation and server code (runs on the board)
settings.toml        # WiFi credentials (CIRCUITPY_WIFI_SSID, CIRCUITPY_WIFI_PASSWORD) — NOT in git
settings.toml.example  # Template for settings.toml
lib/                 # CircuitPython libraries (on the board, not in repo)
  adafruit_bitmap_font/
  adafruit_display_text/
  adafruit_httpserver/
  adafruit_ticks.mpy
```

## Architecture

Everything runs in a single `code.py` — CircuitPython on the MatrixPortal S3 executes `code.py` on boot.

### Display pipeline
- `rgbmatrix.RGBMatrix` → `framebufferio.FramebufferDisplay` at 64x32, bit_depth=6
- Each animation mode has its own `displayio.Group` with layered `TileGrid` + `Bitmap` + `Palette` objects
- Mode switching swaps `display.root_group`
- Color/brightness changes are done via palette manipulation (not bitmap redraws) for efficiency

### Animation modes
1. **Space** — 5-minute cycle (300s) with 6 phases. Parallax star field (3 layers at different scroll speeds), animated nebula palette, pixel-art rocket with thrust animation, shooting stars, scrolling planet, phase-based text messages
2. **Matrix Rain** — Classic green cascade. 20 rain drops with variable speed/length, palette-based fade trail
3. **Rainbow Wave** — 16-color HSV palette scrolling diagonally across the display
4. **Peru** — 5-minute Andes day/night cycle (300s) with 7 phases. Procedural mountain range with animated sky/snow/valley palettes, sun arc, pixel-art llama with woven blanket, condor, scrolling Inca textile pattern, pulsing heart, Spanish love messages

### Web control
- `adafruit_httpserver.Server` on port 80
- Routes: `/`, `/mode/{space,rain,rainbow,peru}`, `/bright/<1-10>`
- Mobile-friendly HTML served inline (no external assets)
- IP address scrolls across the display on startup for discovery

### Input
- Physical buttons cycle through modes (UP = next, DOWN = previous)
- Web UI for mode selection and brightness (1–10 scale, maps to 0.1–1.0 multiplier)

### Main loop
- ~28 FPS target (`time.sleep(0.035)`)
- `server.poll()` handles HTTP requests each frame
- Brightness changes propagate via `bri_changed` flag to update all palettes once
- Animation state (scroll positions, timers, sprite visibility) persists across frames via module-level globals

## Development Notes

- **Deploying:** Copy `code.py` to `/Volumes/CIRCUITPY/` when the board is connected via USB-C. The board auto-reloads
- **Serial console:** `screen /dev/tty.usbmodem*` or use Mu editor for REPL + print debugging
- **Libraries:** Install via `circup` or manually copy from Adafruit CircuitPython Bundle to `lib/`
- **Memory:** CircuitPython on ESP32-S3 has ~2 MB PSRAM heap. Current code uses significant displayio resources — monitor with `gc.mem_free()` if adding features
- **Palette animation is cheap, bitmap mutation is expensive** — prefer palette color changes over per-pixel bitmap writes
- **The board has an accelerometer** (LIS3DH at I2C 0x19) that isn't currently used — available for tilt/tap interactions
- **The NeoPixel and red LED** aren't currently used — available for status indication
- **Fallback WiFi** is hardcoded in code.py (SpectrumSetup-15) as backup if settings.toml SSID fails
