# MatrixPortal S3 — Multi-animation display with phone control via Wi-Fi
# Space: 5-min cycle | Matrix Rain | Peru: for mi amor
# Connect to http://<board-ip> from your phone to switch modes

import time
import random
import math
import board
import displayio
import framebufferio
import rgbmatrix
import terminalio
import wifi
import socketpool
import os
import digitalio
from adafruit_display_text.label import Label
from adafruit_httpserver import Server, Request, Response

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
ip = str(wifi.radio.ipv4_address)
print("Connected! IP:", ip)

pool = socketpool.SocketPool(wifi.radio)
server = Server(pool, debug=False)

# === STATE ===
current_mode = "space"
brightness = 10

# === WEB PAGE ===
HTML = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Matrix Control</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0a0a1a;color:#fff;font-family:-apple-system,sans-serif;
display:flex;flex-direction:column;align-items:center;padding:20px;min-height:100vh}
h1{font-size:1.4em;margin-bottom:24px;color:#8af}
.btn{display:block;width:280px;padding:18px;margin:8px;border:none;border-radius:12px;
font-size:1.1em;font-weight:600;cursor:pointer;transition:transform 0.1s,box-shadow 0.2s}
.btn:active{transform:scale(0.96)}
.space{background:linear-gradient(135deg,#1a1a4e,#2d1b69);color:#ccf;
box-shadow:0 0 20px rgba(100,100,255,0.3)}
.rain{background:linear-gradient(135deg,#0a2e0a,#1a4a1a);color:#6f6;
box-shadow:0 0 20px rgba(0,255,0,0.2)}
.peru{background:linear-gradient(135deg,#8B0000,#CC3333);color:#FFD700;
box-shadow:0 0 20px rgba(255,215,0,0.3)}
.active{box-shadow:0 0 30px rgba(255,255,255,0.4);border:2px solid #fff}
.bright{display:flex;align-items:center;gap:12px;margin-top:20px;width:280px}
.bright label{font-size:0.9em;color:#aaa;white-space:nowrap}
.bright input{flex:1;accent-color:#8af}
.bval{color:#8af;font-size:0.9em;min-width:36px;text-align:center}
.ip{margin-top:24px;font-size:0.8em;color:#556}
</style>
</head>
<body>
<h1>LED Matrix Control</h1>
<button class="btn space SPACE_ACTIVE" onclick="location.href='/mode/space'">Space</button>
<button class="btn rain RAIN_ACTIVE" onclick="location.href='/mode/rain'">Matrix Rain</button>
<button class="btn peru PERU_ACTIVE" onclick="location.href='/mode/peru'">Mi Peru</button>
<div class="bright">
<label>Brightness</label>
<input type="range" min="1" max="10" value="BRIGHT_VAL" oninput="document.getElementById('bv').textContent=this.value*10+'%';fetch('/bright/'+this.value)">
<span class="bval" id="bv">BRIGHT_PCT%</span>
</div>
<p class="ip">IP_ADDR</p>
</body>
</html>"""

def serve_page(mode):
    page = HTML.replace("IP_ADDR", ip)
    page = page.replace("SPACE_ACTIVE", "active" if mode == "space" else "")
    page = page.replace("RAIN_ACTIVE", "active" if mode == "rain" else "")
    page = page.replace("PERU_ACTIVE", "active" if mode == "peru" else "")
    page = page.replace("BRIGHT_VAL", str(brightness))
    page = page.replace("BRIGHT_PCT", str(brightness * 10))
    return page

@server.route("/")
def index(request: Request):
    return Response(request, serve_page(current_mode), content_type="text/html")

@server.route("/mode/space")
def mode_space(request: Request):
    global current_mode
    current_mode = "space"
    return Response(request, serve_page("space"), content_type="text/html")

@server.route("/mode/rain")
def mode_rain(request: Request):
    global current_mode
    current_mode = "rain"
    return Response(request, serve_page("rain"), content_type="text/html")

@server.route("/mode/peru")
def mode_peru(request: Request):
    global current_mode
    current_mode = "peru"
    return Response(request, serve_page("peru"), content_type="text/html")

@server.route("/bright/<level>")
def set_brightness(request: Request, level: str):
    global brightness
    try:
        b = int(level)
        if 1 <= b <= 10:
            brightness = b
            display.brightness = b / 10.0
    except ValueError:
        pass
    return Response(request, "", content_type="text/plain")

server.start(ip, 80)
print("Server running at http://{}".format(ip))

# ======================================================================
# HELPERS
# ======================================================================
def lerp_c(c1, c2, t):
    return (int(c1[0]+(c2[0]-c1[0])*t), int(c1[1]+(c2[1]-c1[1])*t), int(c1[2]+(c2[2]-c1[2])*t))

def rgb_pack(c):
    return (c[0] << 16) | (c[1] << 8) | c[2]

def clamp(val):
    """Clamp a color component: 0 stays 0, non-zero floors to 1."""
    if val <= 0:
        return 0
    return max(1, int(val))

# ======================================================================
# SPACE ANIMATION — 5-MINUTE MESMERIZING CYCLE
# ======================================================================
CYCLE = 300.0
PHASE_T = [0, 50, 100, 170, 220, 270]

NEB = [
    [(0,0,10),(2,0,14),(4,0,8)],
    [(0,8,28),(12,0,36),(8,0,20)],
    [(0,14,34),(16,0,46),(20,0,28)],
    [(14,0,56),(0,20,56),(24,0,40)],
    [(6,0,28),(0,8,20),(10,0,18)],
    [(0,0,10),(2,0,14),(4,0,8)],
]

STAR_SPD = [0.08, 0.3, 1.0, 0.7, 0.2, 0.08]
STAR_BRI = [0.3, 0.6, 1.0, 0.9, 0.5, 0.3]
SHOOT_CH = [0.001, 0.003, 0.006, 0.015, 0.003, 0.001]

PHASE_MSG = [
    [],
    ["STARLIGHT", "AWAKENING"],
    ["DEEP SPACE", "EXPLORATION", "SECTOR 7-G", "ALL SYSTEMS GO", "WARP DRIVE ONLINE"],
    ["COSMIC DRIFT", "INFINITE CALM", "BEYOND", "BREATHE", "WEIGHTLESS"],
    ["FADING LIGHT", "SILENT DRIFT"],
    ["SILENT VOYAGE"],
]

TEXT_INT = [999, 18, 7, 10, 16, 25]
TEXT_COL = [0x223344, 0x446688, 0x4488FF, 0x7766CC, 0x335577, 0x223344]

space_group = displayio.Group()

bg_pal = displayio.Palette(6)
bg_pal[0] = 0x000005; bg_pal[1] = 0x000010; bg_pal[2] = 0x000010
bg_pal[3] = 0x000010; bg_pal[4] = 0x030308; bg_pal[5] = 0x040004

bg_bmp = displayio.Bitmap(W, H, 6)
for _ in range(28):
    cx, cy = random.randint(0, W-1), random.randint(0, H-1)
    c = random.choice([1, 2, 3, 5])
    radius = random.randint(2, 5)
    for dx in range(-radius, radius+1):
        for dy in range(-radius, radius+1):
            if dx*dx+dy*dy <= radius*radius:
                nx, ny = cx+dx, cy+dy
                if 0 <= nx < W and 0 <= ny < H and random.random() < 0.55:
                    bg_bmp[nx, ny] = c
space_group.append(displayio.TileGrid(bg_bmp, pixel_shader=bg_pal))

FAR_BASE = [(0x33,0x33,0x44),(0x22,0x22,0x33),(0x2A,0x2A,0x44)]
MID_BASE = [(0x88,0x88,0xAA),(0x99,0x99,0xBB),(0xAA,0xAA,0x55),(0x88,0x88,0xCC)]
NEAR_BASE = [(0xFF,0xFF,0xFF),(0xDD,0xDD,0xFF),(0xFF,0xFF,0x66),(0xFF,0xDD,0xAA)]

def make_stars(count, base_colors):
    n = len(base_colors)
    pal = displayio.Palette(n+1)
    pal[0] = 0x000000; pal.make_transparent(0)
    for i, c in enumerate(base_colors):
        pal[i+1] = (c[0]<<16)|(c[1]<<8)|c[2]
    bmp = displayio.Bitmap(W*2, H, n+1)
    for _ in range(count):
        bmp[random.randint(0,W*2-1), random.randint(0,H-1)] = random.randint(1, n)
    return bmp, pal

far_bmp, far_pal = make_stars(100, FAR_BASE)
far_grid = displayio.TileGrid(far_bmp, pixel_shader=far_pal)
space_group.append(far_grid)

mid_bmp, mid_pal = make_stars(55, MID_BASE)
mid_grid = displayio.TileGrid(mid_bmp, pixel_shader=mid_pal)
space_group.append(mid_grid)

near_bmp, near_pal = make_stars(24, NEAR_BASE)
near_grid = displayio.TileGrid(near_bmp, pixel_shader=near_pal)
space_group.append(near_grid)

rpal = displayio.Palette(7)
rpal[0] = 0x000000; rpal.make_transparent(0)
rpal[1]=0xDDDDDD; rpal[2]=0x999999; rpal[3]=0xCC2200
rpal[4]=0x3355DD; rpal[5]=0xFF5500; rpal[6]=0xFFFFFF

RW, RH = 12, 10
r_bmp = displayio.Bitmap(RW, RH, 7)
for px,py,pc in [
    (9,4,6),(9,5,6),(10,4,1),(10,5,1),(11,4,6),(11,5,6),
    (4,3,1),(5,3,1),(6,3,1),(7,3,1),(8,3,2),(9,3,2),
    (4,4,1),(5,4,1),(6,4,1),(7,4,1),(8,4,1),
    (4,5,1),(5,5,1),(6,5,1),(7,5,1),(8,5,1),
    (4,6,1),(5,6,1),(6,6,1),(7,6,1),(8,6,2),(9,6,2),
    (7,4,4),(7,5,4),(8,4,4),(8,5,4),
    (3,2,3),(4,2,3),(5,2,3),(2,1,3),(3,1,3),(1,0,3),(2,0,3),
    (3,7,3),(4,7,3),(5,7,3),(2,8,3),(3,8,3),(1,9,3),(2,9,3),
    (3,4,2),(3,5,2),(2,3,2),(2,4,5),(2,5,5),(2,6,2),
]:
    if 0<=px<RW and 0<=py<RH: r_bmp[px,py]=pc

rocket_tg = displayio.TileGrid(r_bmp, pixel_shader=rpal, x=-20, y=11)
space_group.append(rocket_tg)

tpal = displayio.Palette(5)
tpal[0]=0x000000; tpal.make_transparent(0)
THRUST_BASE = [(0xFF,0x44,0x00),(0xFF,0x00,0x00),(0xFF,0xAA,0x00),(0xFF,0xFF,0x44)]
for i,c in enumerate(THRUST_BASE): tpal[i+1]=(c[0]<<16)|(c[1]<<8)|c[2]

TW, TH = 6, 10
t_bmp_a = displayio.Bitmap(TW, TH, 5)
t_bmp_b = displayio.Bitmap(TW, TH, 5)
for px,py,pc in [(0,4,3),(0,5,3),(1,3,1),(1,4,4),(1,5,4),(1,6,1),(2,3,2),(2,4,1),(2,5,1),(2,6,2),(3,4,2),(3,5,2)]:
    if 0<=px<TW and 0<=py<TH: t_bmp_a[px,py]=pc
for px,py,pc in [(0,4,3),(0,5,3),(1,3,1),(1,4,4),(1,5,4),(1,6,1),(2,3,2),(2,4,1),(2,5,1),(2,6,2),(3,3,2),(3,4,1),(3,5,1),(3,6,2),(4,4,2),(4,5,2),(5,4,2),(5,5,3)]:
    if 0<=px<TW and 0<=py<TH: t_bmp_b[px,py]=pc

thrust_tg = displayio.TileGrid(t_bmp_a, pixel_shader=tpal, x=-26, y=11)
space_group.append(thrust_tg)

shoot_pal = displayio.Palette(4)
shoot_pal[0]=0x000000; shoot_pal.make_transparent(0)
shoot_pal[1]=0xFFFFFF; shoot_pal[2]=0xAAAAFF; shoot_pal[3]=0x5555AA
shoot_bmp = displayio.Bitmap(W, H, 4)
shoot_grid = displayio.TileGrid(shoot_bmp, pixel_shader=shoot_pal)
space_group.append(shoot_grid)

txt = Label(terminalio.FONT, text="", color=0x4488FF)
txt.y=28; txt.x=W+10
space_group.append(txt)

planet_pal = displayio.Palette(4)
planet_pal[0]=0x000000; planet_pal.make_transparent(0)
planet_pal[1]=0x334488; planet_pal[2]=0x445599; planet_pal[3]=0x223366
PW, PH = 7, 7
planet_bmp = displayio.Bitmap(PW, PH, 4)
for px,py,pc in [
    (2,0,3),(3,0,3),(4,0,3),(1,1,3),(2,1,1),(3,1,1),(4,1,2),(5,1,3),
    (0,2,3),(1,2,1),(2,2,2),(3,2,1),(4,2,2),(5,2,1),(6,2,3),
    (0,3,3),(1,3,1),(2,3,1),(3,3,2),(4,3,1),(5,3,1),(6,3,3),
    (0,4,3),(1,4,2),(2,4,1),(3,4,1),(4,4,1),(5,4,2),(6,4,3),
    (1,5,3),(2,5,2),(3,5,2),(4,5,1),(5,5,3),(2,6,3),(3,6,3),(4,6,3),
]:
    if 0<=px<PW and 0<=py<PH: planet_bmp[px,py]=pc
planet_tg = displayio.TileGrid(planet_bmp, pixel_shader=planet_pal, x=W+20, y=5)
space_group.append(planet_tg)

# ======================================================================
# PERU ANIMATION — A day in the Andes, for mi amor
# ======================================================================
# 5-minute cycle: night -> sunrise -> morning -> midday -> golden hour -> sunset -> night
# Features: Andes mountains, llama, condor, Inca patterns, pulsing hearts, love messages

PERU_CYCLE = 300.0
PERU_PT = [0, 20, 55, 110, 165, 220, 260]  # phase start times (compressed, less dead time)

# SILHOUETTE ART DESIGN: bright things on BLACK = maximum LED impact
PERU_SKY = [
    (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    (0, 0, 0), (0, 0, 0), (0, 0, 0),
]

# Mountain silhouette colors — COOL tones when sun is up (contrast with orange sun)
# shadow=always BLACK, body=silhouette color, highlight=bright edge
PERU_MTN = [
    [(0,0,0),(50,0,100),(120,40,200)],            # night: purple
    [(0,0,0),(0,60,120),(0,120,220)],             # dawn: blue (contrasts with orange sun)
    [(0,0,0),(0,100,60),(0,200,100)],             # morning: teal-green
    [(0,0,0),(0,120,60),(0,220,100)],             # midday: vivid green
    [(0,0,0),(0,80,140),(0,140,255)],             # golden: blue (contrasts with orange sun)
    [(0,0,0),(100,0,80),(200,0,140)],             # sunset: magenta
    [(0,0,0),(50,0,100),(120,40,200)],            # night: purple
]

# Snow — BRIGHT WHITE dots at peak tips, the brightest pixels on screen
PERU_SNOW = [
    (200,180,255), (255,255,255), (255,255,255), (255,255,255),
    (255,255,200), (255,200,180), (200,180,255),
]

# Valley floor — single bright green line during day, BLACK at night
PERU_GREEN = [
    (0,0,0), (0,60,0), (0,180,0), (0,255,0),
    (0,80,0), (0,40,0), (0,0,0),
]


peru_group = displayio.Group()

# --- Mountain background (SILHOUETTE ART: bright outlines on BLACK) ---
# Palette: 0=black bg, 1=black shadow, 2=mtn body, 3=mtn highlight,
#          4=snow, 5=valley floor
p_pal = displayio.Palette(6)
p_pal[0] = 0x000000  # background: ALWAYS BLACK
p_pal[1] = 0x000000  # mountain shadow: ALWAYS BLACK
p_pal[2] = 0x320064  # mountain body: purple silhouette
p_pal[3] = 0x7828C8  # mountain highlight: bright purple edge
p_pal[4] = 0xC8B4FF  # snow cap: bright white
p_pal[5] = 0x000000  # valley floor: BLACK (night)

p_bmp = displayio.Bitmap(W, H, 6)

# Generate Andes mountain range — SILHOUETTE STYLE
# Mountains are a thin bright outline (top 3-4 rows of silhouette visible),
# everything below fades to black shadow. Only peaks glow.
mtn_peaks = [(6,10,9), (18,5,13), (32,7,11), (46,9,10), (58,13,7)]

for x in range(W):
    top_y = H - 5  # default valley level
    for cx, py, hw in mtn_peaks:
        dx = abs(x - cx)
        if dx < hw:
            my = py + (dx * (H - 5 - py)) // hw
            top_y = min(top_y, my)

    for y in range(H):
        if y < top_y:
            p_bmp[x, y] = 0  # BLACK sky
        else:
            depth = y - top_y
            # Snow: ONLY 1 pixel at the very peak tip of tall mountains
            if depth == 0 and top_y < 9:
                p_bmp[x, y] = 4  # snow cap — single bright pixel
            # Highlight: top 2 rows of mountain (bright edge)
            elif depth < 2:
                p_bmp[x, y] = 3  # highlight (bright ridge line)
            # Body: next 3 rows (visible silhouette)
            elif depth < 5:
                p_bmp[x, y] = 2  # body (silhouette color)
            # Valley floor: bottom 1 row only
            elif y == H - 1:
                p_bmp[x, y] = 5  # valley floor (single green line)
            # Everything else: BLACK shadow (invisible on black bg)
            else:
                p_bmp[x, y] = 1  # shadow = BLACK = disappears

peru_group.append(displayio.TileGrid(p_bmp, pixel_shader=p_pal))

# --- Stars overlay (for night phases — now fill the whole black sky) ---
p_star_pal = displayio.Palette(3)
p_star_pal[0] = 0x000000; p_star_pal.make_transparent(0)
p_star_pal[1] = 0xFFFFFF; p_star_pal[2] = 0xAAAA88

p_star_bmp = displayio.Bitmap(W, H, 3)
# Stars across the full screen — most of it is now black, so stars pop everywhere
for _ in range(65):
    sx, sy = random.randint(0, W-1), random.randint(0, H-4)
    p_star_bmp[sx, sy] = random.choice([1, 2])
p_star_grid = displayio.TileGrid(p_star_bmp, pixel_shader=p_star_pal)
peru_group.append(p_star_grid)

# --- Falling snow overlay ---
snow_pal = displayio.Palette(2)
snow_pal[0] = 0x000000; snow_pal.make_transparent(0)
snow_pal[1] = 0xFFFFFF
snow_bmp = displayio.Bitmap(W, H, 2)
snow_grid = displayio.TileGrid(snow_bmp, pixel_shader=snow_pal)
peru_group.append(snow_grid)

# Snow particles: list of [x, y_float, speed, drift]
NUM_SNOW = 30
snow_flakes = []
for _ in range(NUM_SNOW):
    snow_flakes.append([
        random.randint(0, W-1),
        float(random.randint(-H, H)),
        random.uniform(0.3, 1.0),
        random.uniform(-0.3, 0.3),
    ])

# --- Sun sprite (7x7) ---
sun_pal = displayio.Palette(3)
sun_pal[0] = 0x000000; sun_pal.make_transparent(0)
sun_pal[1] = 0xFF8800; sun_pal[2] = 0xFFCC00  # bold orange/gold — max pop on black

sun_bmp = displayio.Bitmap(7, 7, 3)
for px,py,pc in [
    (2,0,1),(3,0,1),(4,0,1),
    (1,1,1),(2,1,2),(3,1,2),(4,1,2),(5,1,1),
    (0,2,1),(1,2,2),(2,2,2),(3,2,2),(4,2,2),(5,2,2),(6,2,1),
    (0,3,1),(1,3,2),(2,3,2),(3,3,2),(4,3,2),(5,3,2),(6,3,1),
    (0,4,1),(1,4,2),(2,4,2),(3,4,2),(4,4,2),(5,4,2),(6,4,1),
    (1,5,1),(2,5,2),(3,5,2),(4,5,2),(5,5,1),
    (2,6,1),(3,6,1),(4,6,1),
]:
    sun_bmp[px, py] = pc
sun_tg = displayio.TileGrid(sun_bmp, pixel_shader=sun_pal, x=48, y=H)
peru_group.append(sun_tg)

# --- Llama sprite (12x9, facing right, with colorful blanket) ---
ll_pal = displayio.Palette(6)
ll_pal[0] = 0x000000; ll_pal.make_transparent(0)
ll_pal[1] = 0xFFEECC  # cream body
ll_pal[2] = 0xFF2200  # red blanket
ll_pal[3] = 0xFFCC00  # gold blanket
ll_pal[4] = 0x604020  # dark (eye/hooves)
ll_pal[5] = 0xCCAA80  # shadow

LLW, LLH = 12, 9
ll_bmp = displayio.Bitmap(LLW, LLH, 6)
for px,py,pc in [
    # Ears (flipped: head now on left, faces right)
    (2,0,1),(3,0,1),
    # Head
    (1,1,1),(2,1,1),(3,1,1),(4,1,1),(2,1,4),
    # Neck
    (2,2,5),(3,2,1),(4,2,1),
    (3,3,5),(4,3,1),(5,3,1),
    # Body with woven blanket
    (2,4,1),(3,4,1),(4,4,1),(5,4,1),(6,4,2),(7,4,3),(8,4,2),(9,4,1),
    (2,5,1),(3,5,1),(4,5,1),(5,5,1),(6,5,3),(7,5,2),(8,5,3),(9,5,1),(10,5,1),
    # Belly
    (3,6,5),(4,6,1),(5,6,1),(6,6,1),(7,6,1),(8,6,1),(9,6,1),(10,6,5),
    # Tail
    (11,4,1),(11,3,1),
    # Legs
    (3,7,1),(4,7,1),(7,7,1),(8,7,1),
    (4,8,4),(8,8,4),
]:
    if 0<=px<LLW and 0<=py<LLH: ll_bmp[px,py]=pc
llama_tg = displayio.TileGrid(ll_bmp, pixel_shader=ll_pal, x=W+10, y=H)
peru_group.append(llama_tg)

# --- Condor sprite (14x5, soaring silhouette with white collar) ---
cd_pal = displayio.Palette(3)
cd_pal[0] = 0x000000; cd_pal.make_transparent(0)
cd_pal[1] = 0xAAAAAA  # bright gray body — visible against black sky
cd_pal[2] = 0xFFFFFF  # white collar — brightest accent

CDW, CDH = 14, 5
cd_bmp = displayio.Bitmap(CDW, CDH, 3)
for px,py,pc in [
    # Wings spread wide
    (0,2,1),(1,1,1),(2,1,1),(3,0,1),(4,0,1),(5,0,1),
    (8,0,1),(9,0,1),(10,0,1),(11,1,1),(12,1,1),(13,2,1),
    (1,2,1),(2,2,1),(3,1,1),(4,1,1),(5,1,1),
    (8,1,1),(9,1,1),(10,1,1),(11,2,1),(12,2,1),
    # Body
    (5,2,1),(6,2,1),(7,2,1),(8,2,1),
    (6,3,1),(7,3,1),
    # Head
    (6,1,1),(7,1,1),
    # White collar
    (5,1,2),(8,1,2),
    # Tail
    (6,4,1),(7,4,1),
]:
    if 0<=px<CDW and 0<=py<CDH: cd_bmp[px,py]=pc
condor_tg = displayio.TileGrid(cd_bmp, pixel_shader=cd_pal, x=W+20, y=-10)
peru_group.append(condor_tg)

# --- Female llama (same size as male, faces left, purple/blue blanket) ---
ll2_pal = displayio.Palette(6)
ll2_pal[0] = 0x000000; ll2_pal.make_transparent(0)
ll2_pal[1] = 0xFFEEDD  # cream body (slightly lighter than male)
ll2_pal[2] = 0xFF00CC  # hot pink blanket
ll2_pal[3] = 0x00FFFF  # cyan blanket accent
ll2_pal[4] = 0x604020  # dark (eye/hooves)
ll2_pal[5] = 0xDDBB99  # shadow

LL2W, LL2H = 12, 9
ll2_bmp = displayio.Bitmap(LL2W, LL2H, 6)
for px,py,pc in [
    # Ears (head on right, faces left)
    (8,0,1),(9,0,1),
    # Head
    (7,1,1),(8,1,1),(9,1,1),(10,1,1),(9,1,4),
    # Neck
    (7,2,1),(8,2,1),(9,2,5),
    (6,3,1),(7,3,1),(8,3,5),
    # Body with woven blanket (purple/blue pattern)
    (2,4,1),(3,4,2),(4,4,3),(5,4,2),(6,4,1),(7,4,1),(8,4,1),(9,4,1),
    (1,5,1),(2,5,1),(3,5,3),(4,5,2),(5,5,3),(6,5,1),(7,5,1),(8,5,1),(9,5,1),
    # Belly
    (1,6,5),(2,6,1),(3,6,1),(4,6,1),(5,6,1),(6,6,1),(7,6,1),(8,6,5),
    # Tail
    (0,4,1),(0,3,1),
    # Legs
    (3,7,1),(4,7,1),(7,7,1),(8,7,1),
    (3,8,4),(7,8,4),
]:
    if 0<=px<LL2W and 0<=py<LL2H: ll2_bmp[px,py]=pc
llama2_tg = displayio.TileGrid(ll2_bmp, pixel_shader=ll2_pal, x=-20, y=H)
peru_group.append(llama2_tg)

# --- Baby llamas (tiny 5x4 sprites, colored by parent) ---
BW, BH = 5, 4
_baby_pixels = [
    (2,0,1),
    (1,1,1),(2,1,1),
    (0,2,1),(1,2,2),(2,2,1),(3,2,1),  # blanket pixel at (1,2)
    (1,3,3),(3,3,3),
]

# Baby 1 — boy (dad's red/gold blanket)
b1_pal = displayio.Palette(4)
b1_pal[0] = 0x000000; b1_pal.make_transparent(0)
b1_pal[1] = 0xFFEEDD  # cream
b1_pal[2] = 0xFF2200  # dad's red
b1_pal[3] = 0x604020  # hooves
baby1_bmp = displayio.Bitmap(BW, BH, 4)
for px,py,pc in _baby_pixels:
    baby1_bmp[px, py] = pc
baby1_tg = displayio.TileGrid(baby1_bmp, pixel_shader=b1_pal, x=W+10, y=H+10)
peru_group.append(baby1_tg)

# Baby 2 — girl (mom's pink/cyan blanket)
b2_pal = displayio.Palette(4)
b2_pal[0] = 0x000000; b2_pal.make_transparent(0)
b2_pal[1] = 0xFFEEDD  # cream
b2_pal[2] = 0xFF00CC  # mom's pink
b2_pal[3] = 0x604020  # hooves
baby2_bmp = displayio.Bitmap(BW, BH, 4)
for px,py,pc in _baby_pixels:
    baby2_bmp[px, py] = pc
baby2_tg = displayio.TileGrid(baby2_bmp, pixel_shader=b2_pal, x=W+10, y=H+10)
peru_group.append(baby2_tg)

# Baby 3 — boy (dad's red/gold blanket)
b3_pal = displayio.Palette(4)
b3_pal[0] = 0x000000; b3_pal.make_transparent(0)
b3_pal[1] = 0xFFEEDD  # cream
b3_pal[2] = 0xFFCC00  # dad's gold
b3_pal[3] = 0x604020  # hooves
baby3_bmp = displayio.Bitmap(BW, BH, 4)
for px,py,pc in _baby_pixels:
    baby3_bmp[px, py] = pc
baby3_tg = displayio.TileGrid(baby3_bmp, pixel_shader=b3_pal, x=W+10, y=H+10)
peru_group.append(baby3_tg)

BABY_Y = H - BH - 1

# --- Peruvian flag (12x8, vertical red-white-red bands) ---
flag_pal = displayio.Palette(4)
flag_pal[0] = 0x000000; flag_pal.make_transparent(0)
flag_pal[1] = 0xDD0000  # red
flag_pal[2] = 0xFFFFFF  # white
flag_pal[3] = 0xCCAA00  # gold (coat of arms accent)

FLW, FLH = 12, 8
flag_bmp = displayio.Bitmap(FLW, FLH, 4)
for px in range(FLW):
    for py in range(FLH):
        if px < 4:
            flag_bmp[px, py] = 1    # red band
        elif px < 8:
            flag_bmp[px, py] = 2    # white band
        else:
            flag_bmp[px, py] = 1    # red band
# Gold emblem dot in center of white band
for px,py in [(5,3),(6,3),(5,4),(6,4)]:
    flag_bmp[px, py] = 3
# Flag stays in upper left corner, always visible
flag_tg = displayio.TileGrid(flag_bmp, pixel_shader=flag_pal, x=1, y=1)
peru_group.append(flag_tg)

# --- Tiny heart (5x4, appears above llamas when they meet) ---
th_pal = displayio.Palette(2)
th_pal[0] = 0x000000; th_pal.make_transparent(0)
th_pal[1] = 0xFF0000
THW, THH = 7, 6
th_bmp = displayio.Bitmap(THW, THH, 2)
#  .XX.XX.
#  XXXXXXX
#  XXXXXXX
#  .XXXXX.
#  ..XXX..
#  ...X...
for px,py in [
    (1,0),(2,0),(4,0),(5,0),
    (0,1),(1,1),(2,1),(3,1),(4,1),(5,1),(6,1),
    (0,2),(1,2),(2,2),(3,2),(4,2),(5,2),(6,2),
    (1,3),(2,3),(3,3),(4,3),(5,3),
    (2,4),(3,4),(4,4),
    (3,5),
]:
    if 0<=px<THW and 0<=py<THH: th_bmp[px,py]=1
heart_tg = displayio.TileGrid(th_bmp, pixel_shader=th_pal, x=W+10, y=H+10)
peru_group.append(heart_tg)

# ======================================================================
# MATRIX RAIN SETUP
# ======================================================================
rain_group = displayio.Group()

rain_pal = displayio.Palette(6)
RAIN_BASE = [0x000000, 0x003300, 0x006600, 0x00AA00, 0x00FF00, 0xCCFFCC]
for i,c in enumerate(RAIN_BASE): rain_pal[i]=c

rain_bmp = displayio.Bitmap(W, H, 6)
rain_grid = displayio.TileGrid(rain_bmp, pixel_shader=rain_pal)
rain_group.append(rain_grid)

NUM_DROPS = 20
drops = []
for _ in range(NUM_DROPS):
    drops.append({'x':random.randint(0,W-1),'y':random.randint(-H,0),
        'speed':random.randint(1,3),'length':random.randint(4,14),'tick':0})

# ======================================================================
# ANIMATION STATE
# ======================================================================
far_s = mid_s = near_s = 0.0
t_frame = 0
txt_x = float(W)
txt_on = False
txt_t = 0.0
txt_i = 0
frame = 0
prev_mode = ""

# Buttons
btn_up = digitalio.DigitalInOut(board.BUTTON_UP)
btn_up.switch_to_input(pull=digitalio.Pull.UP)
btn_down = digitalio.DigitalInOut(board.BUTTON_DOWN)
btn_down.switch_to_input(pull=digitalio.Pull.UP)
MODES = ["space", "rain", "peru"]
btn_last = True
btn_last2 = True

# Space state
shoots = []
MAX_SHOOTS = 3
planet_shown = False

# Peru state
condor_shown = False
# Llama love story — lonely goatherd style
# 0=idle, 1=llama1 enters alone, 2=lonely pause, 3=llama2 enters,
# 4=approaching, 5=meeting, 6=hearts float up, 7=nuzzle pause,
# 8=leave together, 9=offscreen pause, 10=family returns with baby
llama_phase = 0
llama_timer = 0.0
llama_meet_x = 30

# IP display at startup
ip_label = Label(terminalio.FONT, text="http://" + ip, color=0x33AA66)
ip_label.x = W; ip_label.y = 16
ip_scroll_x = float(W)

cycle_start = time.monotonic()
last = cycle_start
start_time = cycle_start

# ======================================================================
# MAIN LOOP
# ======================================================================
while True:
    now = time.monotonic()
    dt = now - last
    last = now
    frame += 1

    try:
        server.poll()
    except Exception:
        pass

    # Button input
    btn_now = btn_up.value
    btn_now2 = btn_down.value
    if not btn_now and btn_last:
        mi = MODES.index(current_mode)
        current_mode = MODES[(mi + 1) % len(MODES)]
    if not btn_now2 and btn_last2:
        mi = MODES.index(current_mode)
        current_mode = MODES[(mi - 1) % len(MODES)]
    btn_last = btn_now
    btn_last2 = btn_now2

    # Switch display group
    if current_mode != prev_mode:
        if current_mode == "space":
            display.root_group = space_group
        elif current_mode == "rain":
            display.root_group = rain_group
        elif current_mode == "peru":
            display.root_group = peru_group
            cycle_start = now  # reset cycle so llamas start immediately
            llama_phase = 0
        prev_mode = current_mode
        if current_mode == "space" and (now - start_time) < 15:
            if ip_label not in space_group:
                space_group.append(ip_label)

    # Scroll IP label
    if ip_label in space_group:
        ip_scroll_x -= 0.5
        ip_label.x = int(ip_scroll_x)
        if ip_scroll_x < -(len(ip_label.text)*6+10):
            space_group.remove(ip_label)

    # ==================================================================
    # SPACE ANIMATION
    # ==================================================================
    if current_mode == "space":
        cycle_t = (now - cycle_start) % CYCLE
        phase = 0
        for i in range(len(PHASE_T)-1, -1, -1):
            if cycle_t >= PHASE_T[i]:
                phase = i
                break

        p_start = PHASE_T[phase]
        p_end = PHASE_T[phase+1] if phase < len(PHASE_T)-1 else CYCLE
        p_t = (cycle_t - p_start) / (p_end - p_start)
        next_phase = (phase+1) % len(PHASE_T)

        if frame % 3 == 0:
            breath = math.sin(now*0.35)*0.25+0.75
            breath2 = math.sin(now*0.2+1.5)*0.2+0.8
            for ci in range(3):
                c_now = NEB[phase][ci]
                c_next = NEB[next_phase][ci]
                c = lerp_c(c_now, c_next, p_t)
                b = breath if ci != 1 else breath2
                c = (clamp(int(c[0]*b)), clamp(int(c[1]*b)), clamp(int(c[2]*b)))
                bg_pal[ci+1] = rgb_pack(c)

        if frame % 5 == 0:
            bri = STAR_BRI[phase]+(STAR_BRI[next_phase]-STAR_BRI[phase])*p_t
            tw_far = math.sin(now*1.2)*0.12+0.88
            tw_mid = math.sin(now*1.7+1.0)*0.1+0.9
            tw_near = math.sin(now*0.8+2.0)*0.08+0.92
            for i,base_c in enumerate(FAR_BASE):
                m = bri*tw_far
                far_pal[i+1]=rgb_pack((clamp(int(base_c[0]*m)),clamp(int(base_c[1]*m)),clamp(int(base_c[2]*m))))
            for i,base_c in enumerate(MID_BASE):
                m = bri*tw_mid
                mid_pal[i+1]=rgb_pack((clamp(int(base_c[0]*m)),clamp(int(base_c[1]*m)),clamp(int(base_c[2]*m))))
            for i,base_c in enumerate(NEAR_BASE):
                m = bri*tw_near
                near_pal[i+1]=rgb_pack((clamp(min(255,int(base_c[0]*m))),clamp(min(255,int(base_c[1]*m))),clamp(min(255,int(base_c[2]*m)))))

        spd = STAR_SPD[phase]+(STAR_SPD[next_phase]-STAR_SPD[phase])*p_t
        far_s += 0.25*spd; mid_s += 0.6*spd; near_s += 1.3*spd
        if far_s >= W: far_s -= W
        if mid_s >= W: mid_s -= W
        if near_s >= W: near_s -= W
        far_grid.x = -int(far_s); mid_grid.x = -int(mid_s); near_grid.x = -int(near_s)

        if cycle_t < 50: rx=-20; ry=14
        elif cycle_t < 80:
            et=(cycle_t-50)/30.0; ease=et*et*(3.0-2.0*et)
            rx=W+10-ease*(W+10-8); ry=14+math.sin(cycle_t*0.1)*2
        elif cycle_t < 220:
            rx=8+math.sin(cycle_t*0.025)*8; ry=11+math.sin(cycle_t*0.12)*3
        elif cycle_t < 255:
            et=(cycle_t-220)/35.0; ease=et*et*(3.0-2.0*et)
            start_rx=8+math.sin(220*0.025)*8
            rx=start_rx-ease*(start_rx+20); ry=11+math.sin(cycle_t*0.12)*2
        else: rx=-20; ry=14
        rocket_tg.x=int(rx); rocket_tg.y=int(ry)
        thrust_tg.x=int(rx)-6; thrust_tg.y=int(ry)

        if frame % 5 == 0:
            t_frame = 1-t_frame
            thrust_tg.bitmap = t_bmp_b if t_frame else t_bmp_a

        for s in shoots:
            for sx,sy in s[2]: shoot_bmp[sx,sy]=0
        new_shoots=[]
        for s in shoots:
            s[0]-=2.0; s[1]+=0.8; s[2]=[]
            ix,iy=int(s[0]),int(s[1])
            tc=[1,1,2,2,3,3]
            for t in range(6):
                px=ix+t; py=iy-int(t*0.4)
                if 0<=px<W and 0<=py<H:
                    shoot_bmp[px,py]=tc[t]; s[2].append((px,py))
            if ix>-10 and iy<H+5: new_shoots.append(s)
        shoots=new_shoots
        if len(shoots)<MAX_SHOOTS and random.random()<SHOOT_CH[phase]:
            shoots.append([float(W-1+random.randint(0,10)),float(random.randint(0,H//2)),[]])

        if 115<cycle_t<165 and not planet_shown:
            planet_tg.x=W; planet_tg.y=random.randint(2,H-9); planet_shown=True
        if planet_shown:
            if frame%6==0: planet_tg.x-=1
            if planet_tg.x<-PW: planet_shown=False; planet_tg.x=W+20
        if cycle_t<10: planet_shown=False

        txt_t += dt
        msgs=PHASE_MSG[phase]; interval=TEXT_INT[phase]
        if not txt_on and txt_t>=interval and msgs:
            txt_on=True; txt_t=0.0; txt_x=float(W)
            txt.text=msgs[txt_i%len(msgs)]; txt.color=TEXT_COL[phase]; txt_i+=1
        if txt_on:
            txt_x-=0.5; txt.x=int(txt_x)
            if txt_x<-(len(txt.text)*6+10): txt_on=False; txt_t=0.0; txt.x=W+10

    # ==================================================================
    # PERU ANIMATION — a day in the Andes
    # ==================================================================
    elif current_mode == "peru":
        cycle_t = (now - cycle_start) % PERU_CYCLE
        pp = 0
        for i in range(len(PERU_PT)-1, -1, -1):
            if cycle_t >= PERU_PT[i]:
                pp = i
                break

        pp_start = PERU_PT[pp]
        pp_end = PERU_PT[pp+1] if pp < len(PERU_PT)-1 else PERU_CYCLE
        pp_t = (cycle_t - pp_start) / (pp_end - pp_start)
        pp_next = (pp+1) % len(PERU_PT)

        # --- Animate mountain palette (SILHOUETTE on BLACK) ---
        if frame % 3 == 0:
            # Mountain colors (shadow=idx1 always BLACK, body=idx2, highlight=idx3)
            for ci in range(3):
                mc = lerp_c(PERU_MTN[pp][ci], PERU_MTN[pp_next][ci], pp_t)
                p_pal[ci+1] = rgb_pack(mc)

            # Snow — always bright white, single pixels at peaks
            sc = lerp_c(PERU_SNOW[pp], PERU_SNOW[pp_next], pp_t)
            p_pal[4] = rgb_pack(sc)

            # Valley floor — single green line at bottom
            gc = lerp_c(PERU_GREEN[pp], PERU_GREEN[pp_next], pp_t)
            p_pal[5] = rgb_pack(gc)

        # --- Stars (visible at night, fade during day) ---
        star_bri = 0.0
        if pp == 0: star_bri = 1.0 - pp_t * 0.8  # night -> dawn fade
        elif pp == 6: star_bri = 0.2 + pp_t * 0.8  # returning night
        elif pp == 5: star_bri = pp_t * 0.2  # sunset stars appear
        elif pp == 1: star_bri = max(0, 0.2 - pp_t * 0.2)

        if frame % 5 == 0:
            tw = math.sin(now * 1.5) * 0.15 + 0.85
            sb = star_bri * tw
            p_star_pal[1] = rgb_pack((clamp(int(255*sb)), clamp(int(255*sb)), clamp(int(255*sb))))
            p_star_pal[2] = rgb_pack((clamp(int(170*sb)), clamp(int(170*sb)), clamp(int(136*sb))))

        # --- Falling snow ---
        if frame % 2 == 0:
            for flake in snow_flakes:
                # Clear old position
                ox, oy = int(flake[0]), int(flake[1])
                if 0 <= ox < W and 0 <= oy < H:
                    snow_bmp[ox, oy] = 0
                # Move
                flake[1] += flake[2] * dt * 8
                flake[0] += flake[3] + math.sin(now * 2 + flake[0]) * 0.15
                # Wrap
                if flake[1] > H:
                    flake[1] = -1.0
                    flake[0] = random.randint(0, W-1)
                if flake[0] < 0: flake[0] = W - 1
                if flake[0] >= W: flake[0] = 0
                # Draw new position
                nx, ny = int(flake[0]), int(flake[1])
                if 0 <= nx < W and 0 <= ny < H:
                    snow_bmp[nx, ny] = 1
            # Snow brightness — brighter in cold phases (night, dawn, sunset)
            snow_alpha = 0.0
            if pp in (0, 6): snow_alpha = 1.0
            elif pp in (1, 5): snow_alpha = 0.6
            elif pp in (2, 4): snow_alpha = 0.3
            else: snow_alpha = 0.1
            sv = clamp(int(255 * snow_alpha))
            snow_pal[1] = rgb_pack((sv, sv, sv))

        # --- Sun arc (fast rise, slow cruise, fast set) ---
        if 3 < cycle_t < 9:
            # Quick rise from right
            st = (cycle_t - 3) / 6.0
            ease = st * st * (3.0 - 2.0 * st)
            sun_tg.x = W - int(ease * (W - 50))
            sun_tg.y = 18 - int(ease * 16)
        elif 9 <= cycle_t < 200:
            # Slow cruise across the sky
            st = (cycle_t - 9) / 191.0
            sun_tg.x = 50 - int(st * 56)
            sun_tg.y = 2 + int(math.sin(st * math.pi) * 3)
        elif 200 <= cycle_t < 206:
            # Quick set to left
            st = (cycle_t - 200) / 6.0
            ease = st * st * (3.0 - 2.0 * st)
            sun_tg.x = -6 - int(ease * 5)
            sun_tg.y = 5 + int(ease * 14)
        else:
            sun_tg.y = H + 5


        # --- Llama love story — lonely goatherd style (~60-200s) ---
        LLAMA_Y = H - LLH - 1
        LLAMA2_Y = H - LL2H - 1
        HIDE = H + 10

        if cycle_t < 3:
            llama_phase = 0
            llama_tg.x = W + 10; llama_tg.y = HIDE
            llama2_tg.x = -20; llama2_tg.y = HIDE
            heart_tg.x = W + 10; heart_tg.y = HIDE
            baby1_tg.x = W + 10; baby1_tg.y = HIDE
            baby2_tg.x = W + 10; baby2_tg.y = HIDE
            baby3_tg.x = W + 10; baby3_tg.y = HIDE

        # Phase 0 → 1: Lonely llama enters from right
        # Triggers at start of cycle and again after story ends
        if cycle_t > 5 and llama_phase == 0:
            llama_phase = 1
            llama_tg.x = W + 5; llama_tg.y = LLAMA_Y
            llama_timer = now

        # Phase 1: Lonely llama walks to center-right, stops
        if llama_phase == 1:
            if frame % 3 == 0 and llama_tg.x > 38:
                llama_tg.x -= 1
            if llama_tg.x <= 38:
                llama_phase = 2
                llama_timer = now

        # Phase 2: Lonely pause — llama stands alone, looking
        if llama_phase == 2:
            if now - llama_timer > 5.0:
                llama_phase = 3
                llama_timer = now
                llama2_tg.x = -LL2W - 5; llama2_tg.y = LLAMA2_Y

        # Phase 3: Second llama appears from left, walks toward first
        if llama_phase == 3:
            llama2_tg.flip_x = False  # face right (head on right = default)
            if frame % 4 == 0 and llama2_tg.x < llama_meet_x - LL2W - 2:
                llama2_tg.x += 1
            if llama2_tg.x >= llama_meet_x - LL2W - 2:
                llama_phase = 4
                llama_timer = now

        # Phase 4: First llama walks toward second
        if llama_phase == 4:
            if frame % 3 == 0 and llama_tg.x > llama_meet_x + 2:
                llama_tg.x -= 1
            if llama_tg.x <= llama_meet_x + 2:
                llama_phase = 5
                llama_timer = now

        # Phase 5: They meet — pause face to face
        if llama_phase == 5:
            if now - llama_timer > 2.0:
                llama_phase = 6
                llama_timer = now
                heart_tg.x = llama_meet_x - 1
                heart_tg.y = LLAMA_Y - THH - 2

        # Phase 6: Hearts float up — pulsing, rising
        if llama_phase == 6:
            pulse = math.sin(now * 4.0) * 0.3 + 0.7
            th_pal[1] = (max(1, int(255 * pulse)) << 16)
            if frame % 15 == 0:
                heart_tg.y -= 1
            if now - llama_timer > 5.0:
                llama_phase = 7
                llama_timer = now

        # Phase 7: Nuzzle — llamas move 1px closer, heart stays
        if llama_phase == 7:
            if now - llama_timer < 1.0:
                if frame % 10 == 0:
                    if llama_tg.x > llama_meet_x:
                        llama_tg.x -= 1
                    if llama2_tg.x < llama_meet_x - LL2W:
                        llama2_tg.x += 1
            if now - llama_timer > 3.0:
                llama_phase = 8
                llama_timer = now
                heart_tg.x = W + 10; heart_tg.y = HIDE

        # Phase 8: Leave together to the left
        if llama_phase == 8:
            llama2_tg.flip_x = True  # flip to face left (walking left)
            if frame % 3 == 0:
                llama_tg.x -= 1
                llama2_tg.x -= 1
            if llama_tg.x < -LLW - 5:
                llama_phase = 9
                llama_timer = now
                llama_tg.x = W + 10; llama_tg.y = HIDE
                llama2_tg.x = W + 10; llama2_tg.y = HIDE

        # Phase 9: Offscreen pause — they're starting a family
        if llama_phase == 9 and now - llama_timer > 5.0:
            llama_phase = 10
            llama_timer = now
            # Family enters from right: parent1, baby1, baby2, baby3, parent2
            llama_tg.x = W + 5; llama_tg.y = LLAMA_Y
            baby1_tg.x = W + 18; baby1_tg.y = BABY_Y
            baby2_tg.x = W + 25; baby2_tg.y = BABY_Y
            baby3_tg.x = W + 32; baby3_tg.y = BABY_Y
            llama2_tg.x = W + 40; llama2_tg.y = LLAMA2_Y

        # Phase 10: Family returns — parents + 3 babies walk left
        if llama_phase == 10:
            if frame % 2 == 0:
                llama_tg.x -= 1
                baby1_tg.x -= 1
                baby2_tg.x -= 1
                baby3_tg.x -= 1
                llama2_tg.x -= 1
            # Heart above the family
            if llama_tg.x > 5 and llama_tg.x < 50:
                heart_tg.x = llama_tg.x + 2
                heart_tg.y = LLAMA_Y - THH - 2
                pulse = math.sin(now * 3.0) * 0.3 + 0.7
                th_pal[1] = (max(1, int(255 * pulse)) << 16)
            else:
                heart_tg.x = W + 10; heart_tg.y = HIDE
            # All off screen left?
            if llama2_tg.x < -LL2W - 5:
                llama_phase = 0
                llama_tg.x = W + 10; llama_tg.y = HIDE
                llama2_tg.x = -20; llama2_tg.y = HIDE
                baby1_tg.x = W + 10; baby1_tg.y = HIDE
                baby2_tg.x = W + 10; baby2_tg.y = HIDE
                baby3_tg.x = W + 10; baby3_tg.y = HIDE
                heart_tg.x = W + 10; heart_tg.y = HIDE

        # --- Condor (soars during midday ~110-170s) ---
        if 110 < cycle_t < 170 and not condor_shown:
            condor_tg.x = W + 5
            condor_tg.y = random.randint(6, 14)
            condor_shown = True
        if condor_shown:
            if frame % 2 == 0:
                condor_tg.x -= 1
            condor_tg.y = condor_tg.y + (1 if frame % 40 < 20 else -1) if frame % 20 == 0 else condor_tg.y
            if condor_tg.x < -CDW:
                condor_shown = False
                condor_tg.x = W + 20; condor_tg.y = -10
        if cycle_t < 10: condor_shown = False

    # ==================================================================
    # MATRIX RAIN
    # ==================================================================
    elif current_mode == "rain":
        if frame % 2 == 0:
            for y in range(H):
                for x in range(W):
                    v = rain_bmp[x, y]
                    if v > 0: rain_bmp[x, y] = v-1
            for d in drops:
                d['tick'] += 1
                if d['tick'] >= (4-d['speed']):
                    d['tick'] = 0; d['y'] += 1
                    if 0 <= d['y'] < H: rain_bmp[d['x'], d['y']] = 5
                    for t in range(1, d['length']):
                        ty = d['y']-t
                        if 0 <= ty < H:
                            bv = max(1, 4-(t*4//d['length']))
                            rain_bmp[d['x'], ty] = bv
                    if d['y']-d['length'] > H:
                        d['x']=random.randint(0,W-1); d['y']=random.randint(-10,-1)
                        d['speed']=random.randint(1,3); d['length']=random.randint(4,14)

    time.sleep(0.035)
