# ISS Tracker — Standalone mode for MatrixPortal S3 + 64x32 RGB LED matrix
# Full-screen world map with per-continent colors, blinking ISS dot + trail
# Copy this to /Volumes/CIRCUITPY/code.py to run (replaces animations)

import time
import math
import gc
import board
import displayio
import framebufferio
import rgbmatrix
import terminalio
import wifi
import socketpool
import ssl
import os
import digitalio
import adafruit_requests

from iss_worldmap import MAP_W, MAP_H, latlon_to_pixel, init_map, get_continent
from iss_geo import lookup as iss_lookup

# === DISPLAY SETUP ===
displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
    width=64, height=32, bit_depth=6,
    rgb_pins=[
        board.MTX_R1, board.MTX_G1, board.MTX_B1,
        board.MTX_R2, board.MTX_G2, board.MTX_B2,
    ],
    addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
    clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT, output_enable_pin=board.MTX_OE,
)

display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)
W, H = 64, 32

# === WI-FI ===
print("Connecting to Wi-Fi...")
try:
    wifi.radio.connect(
        os.getenv("CIRCUITPY_WIFI_SSID"),
        os.getenv("CIRCUITPY_WIFI_PASSWORD"),
    )
except Exception:
    print("Primary Wi-Fi failed, trying fallback...")
    wifi.radio.connect("SpectrumSetup-15", "ablebeer785")
print("Connected! IP:", wifi.radio.ipv4_address)

pool = socketpool.SocketPool(wifi.radio)
http = adafruit_requests.Session(pool, ssl.create_default_context())

# === CONSTANTS ===
ISS_URL = "https://api.wheretheiss.at/v1/satellites/25544"
FETCH_INTERVAL = 10
LOU_LAT, LOU_LON = 38.2527, -85.7585
TRAIL_MAX = 12

# === STATE ===
iss_lat = iss_lon = iss_alt = iss_vel = 0.0
iss_vis = "unknown"
iss_region = "---"
iss_dist_km = 0
data_ready = False
fail_count = 0
last_fetch = 0.0
blink_time = 0.0
dot_on = True
px = py = -1
trail = []

# === BUTTONS ===
btn_up = digitalio.DigitalInOut(board.BUTTON_UP)
btn_up.switch_to_input(pull=digitalio.Pull.UP)
btn_down = digitalio.DigitalInOut(board.BUTTON_DOWN)
btn_down.switch_to_input(pull=digitalio.Pull.UP)

# === HELPERS ===
def haversine(lat1, lon1, lat2, lon2):
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*
         math.sin(dlon/2)**2)
    return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def fetch():
    global iss_lat, iss_lon, iss_alt, iss_vel, iss_vis
    global iss_region, iss_dist_km, last_fetch, fail_count, data_ready
    try:
        resp = http.get(ISS_URL)
        data = resp.json()
        resp.close()
        iss_lat = data["latitude"]
        iss_lon = data["longitude"]
        iss_alt = data["altitude"]
        iss_vel = data["velocity"]
        iss_vis = data.get("visibility", "unknown")
        iss_region = iss_lookup(iss_lat, iss_lon)
        ground = haversine(LOU_LAT, LOU_LON, iss_lat, iss_lon)
        iss_dist_km = int(math.sqrt(ground*ground + iss_alt*iss_alt))
        last_fetch = time.monotonic()
        fail_count = 0
        data_ready = True
        gc.collect()
        return True
    except Exception as e:
        print("Fetch error:", e)
        fail_count += 1
        if fail_count >= 3:
            try:
                wifi.radio.connect(
                    os.getenv("CIRCUITPY_WIFI_SSID"),
                    os.getenv("CIRCUITPY_WIFI_PASSWORD"),
                )
            except Exception:
                pass
            fail_count = 0
        return False

def restore(x, y):
    if 0 <= x < MAP_W and 0 <= y < MAP_H:
        map_bmp[x, y] = get_continent(x, y)

def update_map():
    global px, py
    for dx, dy in ((0,0), (1,0), (-1,0), (0,-1), (0,1)):
        restore(px+dx, py+dy)
    while len(trail) >= TRAIL_MAX:
        ox, oy = trail.pop(0)
        restore(ox, oy)
    if data_ready and (px, py) not in trail:
        trail.append((px, py))
    for tx, ty in trail:
        if 0 <= tx < W and 0 <= ty < H:
            map_bmp[tx, ty] = 8
    px, py = latlon_to_pixel(iss_lat, iss_lon)
    # Restore Louisville
    if 0 <= lou_px < W and 0 <= lou_py < H:
        map_bmp[lou_px, lou_py] = 9

# === MAP DISPLAY ===
# Palette: 0=ocean(black), 1-6=continents, 7=ISS, 8=trail, 9=Louisville
map_group = displayio.Group()
map_bmp = displayio.Bitmap(W, H, 10)
map_pal = displayio.Palette(10)
map_pal[0] = 0x000000  # ocean: BLACK
map_pal[1] = 0xFFCC00  # North America: yellow-gold
map_pal[2] = 0x00CC44  # South America: green
map_pal[3] = 0x4488FF  # Europe: bright blue
map_pal[4] = 0xFF8800  # Africa: orange
map_pal[5] = 0xCC44AA  # Asia: magenta-pink
map_pal[6] = 0xCC2222  # Oceania: red
map_pal[7] = 0xFFFFFF  # ISS: dynamic (set per-frame based on continent)
map_pal[8] = 0x666666  # trail: dim gray
map_pal[9] = 0xFFFFFF  # Louisville: bright white

# Best contrast color for ISS dot per continent
# Picks the color most different from the continent underneath
ISS_CONTRAST = {
    0: 0xFFFFFF,  # ocean (black) -> white
    1: 0xFF00FF,  # N.America (yellow) -> magenta
    2: 0xFF0000,  # S.America (green) -> red
    3: 0xFFFF00,  # Europe (blue) -> yellow
    4: 0x00FFFF,  # Africa (orange) -> cyan
    5: 0x00FF00,  # Asia (magenta) -> green
    6: 0x00FFFF,  # Oceania (red) -> cyan
}
init_map(map_bmp)
map_group.append(displayio.TileGrid(map_bmp, pixel_shader=map_pal))

# Louisville marker
lou_px, lou_py = latlon_to_pixel(LOU_LAT, LOU_LON)
if 0 <= lou_px < W and 0 <= lou_py < H:
    map_bmp[lou_px, lou_py] = 9

display.root_group = map_group

# === MAIN LOOP ===
print("ISS Tracker running")

# First fetch
while not fetch():
    time.sleep(2)
update_map()

while True:
    now = time.monotonic()

    # Fetch every 10s
    if now - last_fetch >= FETCH_INTERVAL:
        last_fetch = now
        if fetch():
            update_map()

    # Blink ISS cross (4 dots) with contrast color
    if data_ready:
        if now - blink_time >= 0.5:
            blink_time = now
            dot_on = not dot_on
            if dot_on:
                c = get_continent(px, py)
                map_pal[7] = ISS_CONTRAST.get(c, 0xFFFFFF)
                for dx, dy in ((0,0), (1,0), (-1,0), (0,-1), (0,1)):
                    nx, ny = px+dx, py+dy
                    if 0 <= nx < W and 0 <= ny < H:
                        map_bmp[nx, ny] = 7
            else:
                for dx, dy in ((0,0), (1,0), (-1,0), (0,-1), (0,1)):
                    restore(px+dx, py+dy)

    time.sleep(0.1)
