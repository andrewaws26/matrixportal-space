# MatrixPortal S3 — Multi-animation display with phone control via Wi-Fi
# Space: 5-min cycle | Matrix Rain | Rainbow Wave | Peru: for mi amor
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
brightness = 8
bri_mult = 0.8
bri_changed = True

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
.rainbow{background:linear-gradient(135deg,#4a1a2e,#2e1a4a);color:#f8f;
box-shadow:0 0 20px rgba(255,100,255,0.3)}
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
<button class="btn rainbow RAINBOW_ACTIVE" onclick="location.href='/mode/rainbow'">Rainbow Wave</button>
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
    page = page.replace("RAINBOW_ACTIVE", "active" if mode == "rainbow" else "")
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

@server.route("/mode/rainbow")
def mode_rainbow(request: Request):
    global current_mode
    current_mode = "rainbow"
    return Response(request, serve_page("rainbow"), content_type="text/html")

@server.route("/mode/peru")
def mode_peru(request: Request):
    global current_mode
    current_mode = "peru"
    return Response(request, serve_page("peru"), content_type="text/html")

@server.route("/bright/<level>")
def set_brightness(request: Request, level: str):
    global brightness, bri_mult, bri_changed
    try:
        b = int(level)
        if 1 <= b <= 10:
            brightness = b
            bri_mult = b / 10.0
            bri_changed = True
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

def dim(val, m):
    if val == 0:
        return 0
    return max(1, int(val * m))

def dim_hex(c, m):
    return (dim((c>>16)&0xFF,m)<<16)|(dim((c>>8)&0xFF,m)<<8)|dim(c&0xFF,m)

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
PERU_PT = [0, 40, 80, 140, 190, 240, 270]  # phase start times

# Sky colors per phase (r,g,b) — animated via palette
PERU_SKY = [
    (2, 3, 22),        # night: deep blue
    (50, 35, 18),      # dawn: warm amber
    (35, 65, 110),     # morning: bright blue
    (45, 80, 130),     # midday: vivid blue
    (90, 55, 20),      # golden hour: deep gold
    (70, 22, 12),      # sunset: orange-red
    (2, 3, 22),        # night return
]

# Mountain palette targets per phase: shadow, body, highlight
PERU_MTN = [
    [(12,12,22),(22,22,35),(28,28,40)],      # night: blue-gray
    [(40,28,16),(55,40,24),(75,55,35)],       # dawn: warm
    [(28,48,28),(42,65,42),(58,80,55)],       # morning: green
    [(35,55,35),(50,72,48),(65,88,62)],       # midday: bright green
    [(60,38,16),(80,52,25),(100,68,35)],      # golden: warm gold
    [(50,18,12),(68,28,16),(85,38,22)],       # sunset: red
    [(12,12,22),(22,22,35),(28,28,40)],       # night
]

# Snow brightness per phase
PERU_SNOW = [
    (50,50,60), (120,110,100), (220,220,230), (240,240,250),
    (200,180,140), (150,100,80), (50,50,60),
]

# Green valley per phase
PERU_GREEN = [
    (5,12,5), (30,40,15), (25,60,20), (30,70,25),
    (40,50,12), (25,15,8), (5,12,5),
]

PERU_MSG = [
    ["BUENAS NOCHES"],
    ["AMANECE"],
    ["BUENOS DIAS MI AMOR", "QUE LINDO DIA"],
    ["LIBRE COMO EL CONDOR", "PERU MAGICO", "LOS ANDES"],
    ["TE AMO", "MI CORAZON", "ERES MI SOL", "SIEMPRE JUNTOS", "MI VIDA"],
    ["ATARDECER HERMOSO"],
    ["DULCES SUENOS MI AMOR"],
]

PERU_TEXT_INT = [999, 18, 10, 10, 7, 18, 999]
PERU_TEXT_COL = [0x334466, 0xCC8833, 0x4488CC, 0x3388AA, 0xDD4444, 0xCC6622, 0x334466]

peru_group = displayio.Group()

# --- Mountain background (static bitmap, palette animated for time-of-day) ---
p_pal = displayio.Palette(8)
p_pal[0] = 0x020316  # sky (animated)
p_pal[1] = 0x161622  # mountain shadow
p_pal[2] = 0x222235  # mountain body
p_pal[3] = 0x2C2C40  # mountain highlight
p_pal[4] = 0x383850  # snow cap
p_pal[5] = 0x0A1A0A  # green valley
p_pal[6] = 0x000000  # spare
p_pal[7] = 0x000000  # spare

p_bmp = displayio.Bitmap(W, H, 8)

# Generate Andes mountain range
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
            p_bmp[x, y] = 0  # sky
        else:
            depth = y - top_y
            total = max(1, H - top_y)
            if depth < 2 and top_y < 9:
                p_bmp[x, y] = 4  # snow cap
            elif depth < total * 35 // 100:
                p_bmp[x, y] = 3  # highlight
            elif depth < total * 65 // 100:
                p_bmp[x, y] = 2  # body
            elif y >= H - 4:
                p_bmp[x, y] = 5  # green valley
            else:
                p_bmp[x, y] = 1  # shadow

peru_group.append(displayio.TileGrid(p_bmp, pixel_shader=p_pal))

# --- Stars overlay (for night phases) ---
p_star_pal = displayio.Palette(3)
p_star_pal[0] = 0x000000; p_star_pal.make_transparent(0)
p_star_pal[1] = 0xFFFFFF; p_star_pal[2] = 0xAAAA88

p_star_bmp = displayio.Bitmap(W, H, 3)
for _ in range(50):
    sx, sy = random.randint(0, W-1), random.randint(0, 18)
    p_star_bmp[sx, sy] = random.choice([1, 2])
p_star_grid = displayio.TileGrid(p_star_bmp, pixel_shader=p_star_pal)
peru_group.append(p_star_grid)

# --- Sun sprite (7x7) ---
sun_pal = displayio.Palette(3)
sun_pal[0] = 0x000000; sun_pal.make_transparent(0)
sun_pal[1] = 0xFFCC00; sun_pal[2] = 0xFFEE44

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
ll_pal[1] = 0xEEDDCC  # cream body
ll_pal[2] = 0xCC1111  # red blanket
ll_pal[3] = 0xDDAA00  # gold blanket
ll_pal[4] = 0x221100  # dark (eye/hooves)
ll_pal[5] = 0xBBAA99  # shadow

LLW, LLH = 12, 9
ll_bmp = displayio.Bitmap(LLW, LLH, 6)
for px,py,pc in [
    # Ears
    (8,0,1),(9,0,1),
    # Head
    (7,1,1),(8,1,1),(9,1,1),(10,1,1),(9,1,4),
    # Neck
    (7,2,1),(8,2,1),(9,2,5),
    (6,3,1),(7,3,1),(8,3,5),
    # Body with woven blanket
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
    if 0<=px<LLW and 0<=py<LLH: ll_bmp[px,py]=pc
llama_tg = displayio.TileGrid(ll_bmp, pixel_shader=ll_pal, x=W+10, y=H)
peru_group.append(llama_tg)

# --- Condor sprite (14x5, soaring silhouette with white collar) ---
cd_pal = displayio.Palette(3)
cd_pal[0] = 0x000000; cd_pal.make_transparent(0)
cd_pal[1] = 0x111111  # black body
cd_pal[2] = 0xDDDDDD  # white collar

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

# --- Inca pattern band (128x5, scrolling geometric textile) ---
inca_pal = displayio.Palette(5)
inca_pal[0] = 0x000000; inca_pal.make_transparent(0)
inca_pal[1] = 0xBB1111  # deep red
inca_pal[2] = 0xDDAA00  # gold
inca_pal[3] = 0xEEDDCC  # cream
inca_pal[4] = 0xCC5500  # orange

IW, IH = 128, 5
inca_bmp = displayio.Bitmap(IW, IH, 5)
# Repeating stepped diamond pattern
for x in range(IW):
    for y in range(IH):
        px = x % 10
        # Two diamonds per 10-pixel period
        d1 = abs(px - 2) + abs(y - 2)
        d2 = abs(px - 7) + abs(y - 2)
        d = min(d1, d2)
        if d == 0:
            inca_bmp[x, y] = 3  # cream center
        elif d == 1:
            inca_bmp[x, y] = 2  # gold ring
        elif d == 2:
            inca_bmp[x, y] = 1  # red ring

inca_tg = displayio.TileGrid(inca_bmp, pixel_shader=inca_pal, x=0, y=H+5)
peru_group.append(inca_tg)

# --- Heart sprite (7x6, pulsing red) ---
ht_pal = displayio.Palette(2)
ht_pal[0] = 0x000000; ht_pal.make_transparent(0)
ht_pal[1] = 0xDD0000

HTW, HTH = 7, 6
ht_bmp = displayio.Bitmap(HTW, HTH, 2)
for px,py in [
    (1,0),(2,0),(4,0),(5,0),
    (0,1),(1,1),(2,1),(3,1),(4,1),(5,1),(6,1),
    (0,2),(1,2),(2,2),(3,2),(4,2),(5,2),(6,2),
    (1,3),(2,3),(3,3),(4,3),(5,3),
    (2,4),(3,4),(4,4),
    (3,5),
]:
    if 0<=px<HTW and 0<=py<HTH: ht_bmp[px,py]=1
heart_tg = displayio.TileGrid(ht_bmp, pixel_shader=ht_pal, x=W+10, y=H+10)
peru_group.append(heart_tg)

# --- Peru text label ---
p_txt = Label(terminalio.FONT, text="", color=0xCC8833)
p_txt.y = 28; p_txt.x = W+10
peru_group.append(p_txt)

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
# RAINBOW WAVE SETUP
# ======================================================================
rainbow_group = displayio.Group()

rb_pal = displayio.Palette(16)
for i in range(16):
    angle = (i/16)*2*math.pi
    r = int((math.sin(angle)*0.5+0.5)*255)
    g = int((math.sin(angle+2.094)*0.5+0.5)*255)
    b = int((math.sin(angle+4.189)*0.5+0.5)*255)
    rb_pal[i] = (r<<16)|(g<<8)|b

rb_bmp = displayio.Bitmap(W, H, 16)
rb_grid = displayio.TileGrid(rb_bmp, pixel_shader=rb_pal)
rainbow_group.append(rb_grid)

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
MODES = ["space", "rain", "rainbow", "peru"]
btn_last = True
btn_last2 = True

# Space state
shoots = []
MAX_SHOOTS = 3
planet_shown = False

# Peru state
p_txt_x = float(W)
p_txt_on = False
p_txt_t = 0.0
p_txt_i = 0
llama_shown = False
condor_shown = False
inca_shown = False
heart_shown = False
heart_floats = []  # floating heart positions

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
        elif current_mode == "rainbow":
            display.root_group = rainbow_group
        elif current_mode == "peru":
            display.root_group = peru_group
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
                c = (dim(int(c[0]*b), bri_mult), dim(int(c[1]*b), bri_mult), dim(int(c[2]*b), bri_mult))
                bg_pal[ci+1] = rgb_pack(c)

        if frame % 5 == 0:
            bri = STAR_BRI[phase]+(STAR_BRI[next_phase]-STAR_BRI[phase])*p_t
            tw_far = math.sin(now*1.2)*0.12+0.88
            tw_mid = math.sin(now*1.7+1.0)*0.1+0.9
            tw_near = math.sin(now*0.8+2.0)*0.08+0.92
            for i,base_c in enumerate(FAR_BASE):
                m = bri*tw_far
                far_pal[i+1]=rgb_pack((dim(int(base_c[0]*m),bri_mult),dim(int(base_c[1]*m),bri_mult),dim(int(base_c[2]*m),bri_mult)))
            for i,base_c in enumerate(MID_BASE):
                m = bri*tw_mid
                mid_pal[i+1]=rgb_pack((dim(int(base_c[0]*m),bri_mult),dim(int(base_c[1]*m),bri_mult),dim(int(base_c[2]*m),bri_mult)))
            for i,base_c in enumerate(NEAR_BASE):
                m = bri*tw_near
                near_pal[i+1]=rgb_pack((dim(min(255,int(base_c[0]*m)),bri_mult),dim(min(255,int(base_c[1]*m)),bri_mult),dim(min(255,int(base_c[2]*m)),bri_mult)))

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

        if bri_changed:
            for i,c in enumerate(THRUST_BASE):
                tpal[i+1]=rgb_pack((dim(c[0],bri_mult),dim(c[1],bri_mult),dim(c[2],bri_mult)))
            shoot_pal[1]=dim_hex(0xFFFFFF,bri_mult)
            shoot_pal[2]=dim_hex(0xAAAAFF,bri_mult)
            shoot_pal[3]=dim_hex(0x5555AA,bri_mult)
            planet_pal[1]=dim_hex(0x334488,bri_mult)
            planet_pal[2]=dim_hex(0x445599,bri_mult)
            planet_pal[3]=dim_hex(0x223366,bri_mult)

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

        # --- Animate sky + mountain palette ---
        if frame % 3 == 0:
            # Sky color
            sky = lerp_c(PERU_SKY[pp], PERU_SKY[pp_next], pp_t)
            p_pal[0] = rgb_pack((dim(sky[0],bri_mult), dim(sky[1],bri_mult), dim(sky[2],bri_mult)))

            # Mountain colors
            for ci in range(3):
                mc = lerp_c(PERU_MTN[pp][ci], PERU_MTN[pp_next][ci], pp_t)
                p_pal[ci+1] = rgb_pack((dim(mc[0],bri_mult), dim(mc[1],bri_mult), dim(mc[2],bri_mult)))

            # Snow
            sc = lerp_c(PERU_SNOW[pp], PERU_SNOW[pp_next], pp_t)
            p_pal[4] = rgb_pack((dim(sc[0],bri_mult), dim(sc[1],bri_mult), dim(sc[2],bri_mult)))

            # Green valley
            gc = lerp_c(PERU_GREEN[pp], PERU_GREEN[pp_next], pp_t)
            p_pal[5] = rgb_pack((dim(gc[0],bri_mult), dim(gc[1],bri_mult), dim(gc[2],bri_mult)))

        # --- Stars (visible at night, fade during day) ---
        star_bri = 0.0
        if pp == 0: star_bri = 1.0 - pp_t * 0.8  # night -> dawn fade
        elif pp == 6: star_bri = 0.2 + pp_t * 0.8  # returning night
        elif pp == 5: star_bri = pp_t * 0.2  # sunset stars appear
        elif pp == 1: star_bri = max(0, 0.2 - pp_t * 0.2)

        if frame % 5 == 0:
            tw = math.sin(now * 1.5) * 0.15 + 0.85
            sb = star_bri * tw * bri_mult
            p_star_pal[1] = rgb_pack((dim(int(255*sb), 1.0), dim(int(255*sb), 1.0), dim(int(255*sb), 1.0)))
            p_star_pal[2] = rgb_pack((dim(int(170*sb), 1.0), dim(int(170*sb), 1.0), dim(int(136*sb), 1.0)))

        # --- Sun position (rises during dawn, sets during sunset) ---
        if 30 < cycle_t < 90:
            # Rising (60 seconds)
            st = (cycle_t - 30) / 60.0
            sun_tg.x = 48 - int(st * 15)
            sun_tg.y = H - 3 - int(st * (H - 5))
        elif 90 <= cycle_t < 230:
            # Arcing across sky
            st = (cycle_t - 90) / 140.0
            sun_tg.x = 33 - int(st * 28)
            sun_tg.y = 2 + int(math.sin(st * math.pi) * 3)
        elif 230 <= cycle_t < 280:
            # Setting
            st = (cycle_t - 230) / 50.0
            sun_tg.x = 5 + int(st * 5)
            sun_tg.y = 2 + int(st * (H - 2))
        else:
            sun_tg.y = H + 5  # hidden below

        # Sun brightness by phase
        if frame % 4 == 0 and bri_changed or frame % 20 == 0:
            sun_pal[1] = dim_hex(0xFFCC00, bri_mult)
            sun_pal[2] = dim_hex(0xFFEE44, bri_mult)

        # --- Llama (walks during morning phase ~85-130s) ---
        if 85 < cycle_t < 135 and not llama_shown:
            llama_tg.x = W + 5
            # Place llama on the valley floor
            llama_tg.y = H - LLH - 1
            llama_shown = True
        if llama_shown:
            if frame % 3 == 0:
                llama_tg.x -= 1
            if llama_tg.x < -LLW:
                llama_shown = False
                llama_tg.x = W + 10; llama_tg.y = H + 5
        if cycle_t < 10: llama_shown = False

        # Llama brightness
        if bri_changed:
            ll_pal[1] = dim_hex(0xEEDDCC, bri_mult)
            ll_pal[2] = dim_hex(0xCC1111, bri_mult)
            ll_pal[3] = dim_hex(0xDDAA00, bri_mult)
            ll_pal[4] = dim_hex(0x221100, bri_mult)
            ll_pal[5] = dim_hex(0xBBAA99, bri_mult)

        # --- Condor (soars during midday phase ~145-185s) ---
        if 145 < cycle_t < 185 and not condor_shown:
            condor_tg.x = W + 5
            condor_tg.y = random.randint(2, 8)
            condor_shown = True
        if condor_shown:
            if frame % 2 == 0:
                condor_tg.x -= 1
            # Gentle vertical bob
            condor_tg.y = condor_tg.y + (1 if frame % 40 < 20 else -1) if frame % 20 == 0 else condor_tg.y
            if condor_tg.x < -CDW:
                condor_shown = False
                condor_tg.x = W + 20; condor_tg.y = -10
        if cycle_t < 10: condor_shown = False

        if bri_changed:
            cd_pal[1] = dim_hex(0x111111, bri_mult)
            cd_pal[2] = dim_hex(0xDDDDDD, bri_mult)

        # --- Inca pattern band (appears during midday/golden ~150-235s) ---
        if 150 < cycle_t < 235:
            if not inca_shown:
                inca_tg.y = H - IH
                inca_shown = True
            # Scroll pattern
            if frame % 3 == 0:
                inca_tg.x -= 1
                if inca_tg.x < -W:
                    inca_tg.x = 0
        else:
            if inca_shown:
                inca_tg.y = H + 5
                inca_shown = False

        if bri_changed:
            inca_pal[1] = dim_hex(0xBB1111, bri_mult)
            inca_pal[2] = dim_hex(0xDDAA00, bri_mult)
            inca_pal[3] = dim_hex(0xEEDDCC, bri_mult)
            inca_pal[4] = dim_hex(0xCC5500, bri_mult)

        # --- Pulsing heart (visible during golden hour ~195-235s) ---
        if 195 < cycle_t < 235:
            if not heart_shown:
                heart_tg.x = 2
                heart_tg.y = 3
                heart_shown = True
            # Heartbeat pulse via palette
            pulse = math.sin(now * 3.5) * 0.3 + 0.7
            hr = int(220 * pulse * bri_mult)
            hg = int(20 * pulse * bri_mult)
            ht_pal[1] = (max(1,hr) << 16) | (max(1,hg) << 8)
        else:
            if heart_shown:
                heart_tg.x = W + 10; heart_tg.y = H + 10
                heart_shown = False

        # --- Scrolling text ---
        p_txt_t += dt
        p_msgs = PERU_MSG[pp]
        p_interval = PERU_TEXT_INT[pp]

        if not p_txt_on and p_txt_t >= p_interval and p_msgs:
            p_txt_on = True; p_txt_t = 0.0; p_txt_x = float(W)
            p_txt.text = p_msgs[p_txt_i % len(p_msgs)]
            p_txt.color = dim_hex(PERU_TEXT_COL[pp], bri_mult)
            p_txt_i += 1
        if p_txt_on:
            p_txt_x -= 0.5
            p_txt.x = int(p_txt_x)
            if p_txt_x < -(len(p_txt.text)*6+10):
                p_txt_on = False; p_txt_t = 0.0; p_txt.x = W+10

    # ==================================================================
    # MATRIX RAIN
    # ==================================================================
    elif current_mode == "rain":
        if bri_changed:
            for i in range(1, 6):
                rain_pal[i] = dim_hex(RAIN_BASE[i], bri_mult)
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

    # ==================================================================
    # RAINBOW WAVE
    # ==================================================================
    elif current_mode == "rainbow":
        if bri_changed:
            for i in range(16):
                angle=(i/16)*2*math.pi
                r=int((math.sin(angle)*0.5+0.5)*255)
                g=int((math.sin(angle+2.094)*0.5+0.5)*255)
                b=int((math.sin(angle+4.189)*0.5+0.5)*255)
                rb_pal[i]=rgb_pack((dim(r,bri_mult),dim(g,bri_mult),dim(b,bri_mult)))
        if frame % 2 == 0:
            offset = frame // 2
            for y in range(H):
                for x in range(W):
                    rb_bmp[x, y] = (x+y+offset) % 16

    bri_changed = False
    time.sleep(0.035)
