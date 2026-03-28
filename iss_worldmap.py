# iss_worldmap.py — 64x32 world map loader
# Reads continent data from map.bin (2048 bytes, one per pixel)
# IDs: 0=ocean 1=NAmerica 2=SAmerica 3=Europe 4=Africa 5=Asia 6=Oceania

MAP_W, MAP_H = 64, 32
LAT_TOP = 80.0
LAT_BOT = -60.0
LON_LEFT = -180.0
LON_RIGHT = 180.0

with open("map.bin", "rb") as _f:
    MAP_PIXELS = _f.read()

def latlon_to_pixel(lat, lon):
    x = int((lon - LON_LEFT) / (LON_RIGHT - LON_LEFT) * MAP_W)
    y = int((LAT_TOP - lat) / (LAT_TOP - LAT_BOT) * MAP_H)
    return max(0, min(MAP_W - 1, x)), max(0, min(MAP_H - 1, y))

def get_continent(x, y):
    if 0 <= x < MAP_W and 0 <= y < MAP_H:
        return MAP_PIXELS[y * MAP_W + x]
    return 0

def init_map(bitmap):
    for y in range(MAP_H):
        for x in range(MAP_W):
            c = MAP_PIXELS[y * MAP_W + x]
            if c > 0:
                bitmap[x, y] = c
