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

### Memory Constraints (learned the hard way)
- **SSL + adafruit_requests + display bitmaps for 3 animation modes = too much for one file.** Importing `ssl` and `adafruit_requests` at startup alongside all animation bitmaps causes crashes. Heavy network features must be in a separate standalone file (see `iss_tracker.py`).
- **Large Python data literals crash the parser.** A `bytes([...])` with 2048 comma-separated integers will crash CircuitPython. Use binary files (`map.bin`) loaded with `open("map.bin", "rb").read()` instead.
- **Lazy imports help** but won't save you if the base animation code already uses most of the memory.

## Project Structure

```
code.py                # Main animations (Space, Rain, Peru) + web server
iss_tracker.py         # Standalone ISS tracker (swap in as code.py to run)
iss_worldmap.py        # World map loader (reads map.bin)
iss_geo.py             # Reverse geocoding (country/ocean lookup from lat/lon)
map.bin                # 64x32 binary map data (2048 bytes, generated from real map image)
settings.toml          # WiFi credentials — NOT in git
settings.toml.example  # Template for settings.toml
CLAUDE.md              # This file
```

### Switching between modes
- **Animations:** `cp code.py /Volumes/CIRCUITPY/code.py`
- **ISS Tracker:** `cp iss_tracker.py /Volumes/CIRCUITPY/code.py`
- Both need `iss_worldmap.py`, `iss_geo.py`, `map.bin` on CIRCUITPY for ISS mode

## Visual Design Principles

**These are the most important rules for this project.** Every animation must follow them or it will look bad on the LED matrix.

### The #1 Rule: Bright things on BLACK backgrounds
- The Space animation works because it's bright dots/sprites on pure black. Peru was redesigned the same way — silhouette mountains, black sky, bright sprites.
- **Never fill the entire screen with color.** Filling every pixel with shades of brown/blue/green creates an indistinguishable muddy mess. Let 60-80% of pixels be OFF (black).
- Black is free — it's LEDs turned off. Use it aggressively as negative space.

### Silhouette art approach
- Landscapes don't work as filled colored regions at 64x32. Instead, use **silhouettes** — a thin bright outline/ridgeline against black.
- Mountains: only the top 3-5 rows of each peak should be lit (highlight + body). Everything below is black shadow.
- The SHAPE of the outline tells the viewer what it is. The fill is wasted pixels.

### Sprite design
- Sprites are the stars of any scene. They should be the brightest, most detailed things on screen.
- Keep sprites **high contrast** against whatever background they'll appear on.
- Use `TileGrid.flip_x` to reverse direction instead of creating mirrored copies.
- Give each character **distinct palette colors** so they're immediately distinguishable (e.g., red/gold blanket vs pink/cyan blanket for llamas).
- Transparent pixels (palette index 0 with `make_transparent(0)`) let the background show through.

### Animation pacing
- **Start action immediately.** Don't make the viewer wait 30+ seconds for something to happen. First visible movement should occur within 5 seconds.
- **Fast transitions, slow cruises.** Rising/entering/exiting should be quick (6-12 seconds). Sustained movement across the sky/screen should be slow and smooth (150-200 seconds).
- Use eased motion (`ease = t*t*(3-2*t)`) for natural-feeling starts/stops. Linear motion looks mechanical.
- **Reset the cycle when switching modes** so the user sees the animation from the beginning, not from wherever the global timer happens to be.

### Storytelling with sprites
- Simple state machines work well for multi-phase stories (lonely goatherd llama love story has 11 phases).
- Each phase should have **visible action** — don't waste time on phases where nothing moves.
- When sprites change direction, flip them so they face the way they're walking.
- Repeating stories should loop automatically — don't tie them to a single window in the cycle.
- For "family" scenes, give offspring visual traits from both parents (blanket colors).

### Particle effects
- Falling snow, shooting stars, and rain all use the same pattern: a list of particles with position, speed, and drift, updated each frame on a transparent overlay bitmap.
- Vary brightness by scene phase (snow brighter at night, dimmer at midday).
- Use sinusoidal drift for natural-looking movement.

## Color Selection Guidelines

This panel has NO gamma correction and only 64 levels per channel (bit_depth=6). Colors that look fine on a monitor will look like mud on the LEDs.

### Minimum brightness
- Any color component meant to be visible must be **>=0x28 (40)** in 8-bit hex terms
- Components below 0x14 (20) are essentially invisible
- The bottom 16 of 64 levels cover 0-50% perceived brightness; everything below level 8 looks nearly identical

### Green dominance
- Green is **3.4x brighter than red** and **10x brighter than blue** at the same drive level
- Equal RGB values (e.g. 0x404040) look green, not gray
- For balanced yellow: use high red + reduced green (e.g. 0xFF5500, not 0xFFFF00)
- For white: reduce green (e.g. 0xFFA8FF rather than 0xFFFFFF)

### Contrast between elements
- Adjacent elements must differ in **hue**, not just brightness — two dark browns are indistinguishable
- Minimum dominant-channel difference between neighbors: **0x30 (48)** in 8-bit hex
- Use complementary colors: red/cyan, blue/yellow, green/magenta give maximum contrast
- When a bright sprite (like the sun) passes near other elements, those elements must be a **contrasting hue** (e.g., blue/green mountains when orange sun is overhead)

### Dynamic contrast (ISS tracker pattern)
- When a marker needs to be visible on any background, dynamically pick the complementary color based on what's underneath:
  - Over black → white
  - Over yellow → magenta
  - Over green → red
  - Over blue → yellow
  - Over orange → cyan
  - Over red → cyan

### Palette design
- Start with high-saturation primaries and secondaries at levels 40-63 (0x66-0xFF)
- Reserve levels 0-15 (0x00-0x28) only for backgrounds and subtle accents
- The safely distinguishable hues: black, white, red, green, blue, yellow, cyan, magenta, orange, pink
- Do NOT use muted/desaturated colors (dusty rose, slate gray, olive, etc.) — they collapse to identical values
- Do NOT port web/monitor hex colors directly — they will look wrong
- For multi-region maps, use maximally separated hues per region (teal, green, blue, orange, magenta, red)

### Testing
- Always verify colors on the actual panel, not on a monitor
- Check in the deployment lighting conditions — ambient light kills the lowest ~5 levels
- At 4mm pitch from 1+ meter, adjacent dim pixels merge — use black borders or outlines to separate regions

## Architecture

Everything runs in a single `code.py` — CircuitPython on the MatrixPortal S3 executes `code.py` on boot.

### Display pipeline
- `rgbmatrix.RGBMatrix` → `framebufferio.FramebufferDisplay` at 64x32, bit_depth=6
- Each animation mode has its own `displayio.Group` with layered `TileGrid` + `Bitmap` + `Palette` objects
- Mode switching swaps `display.root_group`
- Color changes are done via palette manipulation (not bitmap redraws) for efficiency
- Brightness uses `display.brightness` (OE pin PWM duty cycle) for hardware-level dimming

### Animation modes (code.py)
1. **Space** — 5-minute cycle with 6 phases. Parallax star field (3 layers), animated nebula palette, pixel-art rocket with thrust, shooting stars, scrolling planet, phase-based text messages
2. **Matrix Rain** — Classic green cascade. 20 rain drops with variable speed/length, palette-based fade trail
3. **Peru** — Silhouette art: black sky, glowing mountain ridgelines, falling snow, sun arc, llama love story (lonely goatherd style with 11 phases — meet, heart, leave, return with 3 babies), condor, Peruvian flag in corner

### ISS Tracker (iss_tracker.py — standalone)
- Full-screen 64x32 world map generated from real satellite imagery
- Per-continent colors (6 continents, each a different hue)
- Blinking ISS dot with dynamic contrast color based on continent underneath
- Orbital trail (last 12 positions)
- Louisville KY marker (bright white)
- Fetches from `api.wheretheiss.at` every 10 seconds

### Web control
- `adafruit_httpserver.Server` on port 80
- Routes: `/`, `/mode/{space,rain,peru}`, `/bright/<1-10>`
- Mobile-friendly HTML served inline (no external assets)
- IP address scrolls across the display on startup for discovery

### Input
- Physical buttons cycle through modes (UP = next, DOWN = previous)
- Web UI for mode selection and brightness (1-10 scale, maps to `display.brightness` 0.1-1.0)

### Main loop
- ~28 FPS target (`time.sleep(0.035)`) for animations
- ~10 FPS (`time.sleep(0.1)`) for ISS tracker (network overhead, no smooth animation needed)
- `server.poll()` handles HTTP requests each frame
- Animation state persists across frames via module-level globals

## Development Notes

- **Deploying:** Copy files to `/Volumes/CIRCUITPY/` when the board is connected via USB-C. The board auto-reloads on file change.
- **Serial console:** `screen /dev/tty.usbmodem*` or use Mu editor. Serial reads can be flaky — use Python subprocess with timeout if `cat` doesn't work.
- **Libraries:** Install via `circup install <name>` or manually copy from Adafruit CircuitPython Bundle to `lib/`
- **Memory:** Monitor with `gc.mem_free()`. Call `gc.collect()` after network operations.
- **Generating map data:** Use Pillow on the Mac to process real equirectangular map images into 64x32 continent-classified pixel data, then save as binary file. Never embed large data as Python literals.
- **Palette animation is cheap, bitmap mutation is expensive** — prefer palette color changes over per-pixel bitmap writes
- **The board has an accelerometer** (LIS3DH at I2C 0x19) that isn't currently used — available for tilt/tap interactions
- **The NeoPixel and red LED** aren't currently used — available for status indication
- **Fallback WiFi** is hardcoded in code.py (SpectrumSetup-15) as backup if settings.toml SSID fails
