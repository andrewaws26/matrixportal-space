# iss_geo.py — Lightweight reverse geocoding for ISS tracker
# ~50 bounding boxes for countries and oceans
# ISS orbit: 51.6° inclination, covers ~52°N to ~52°S

# Each region: (lat_min, lat_max, lon_min, lon_max, "NAME")
# Countries listed first (more specific), oceans last (catch-all)
REGIONS = [
    # North America
    (49, 72, -141, -52, "CANADA"),
    (25, 49, -125, -66, "USA"),
    (48, 60, -170, -141, "ALASKA"),
    (15, 33, -118, -86, "MEXICO"),
    (7, 18, -92, -77, "C AMERICA"),
    (18, 24, -85, -74, "CUBA"),

    # South America
    (1, 12, -74, -60, "VENEZUELA"),
    (-5, 6, -80, -67, "COLOMBIA"),
    (-2, 2, -82, -75, "ECUADOR"),
    (-18, -1, -82, -69, "PERU"),
    (-23, -10, -70, -57, "BOLIVIA"),
    (-34, -5, -58, -34, "BRAZIL"),
    (-56, -22, -74, -64, "ARGENTINA"),
    (-56, -18, -76, -67, "CHILE"),
    (-35, -30, -59, -53, "URUGUAY"),
    (-27, -19, -63, -54, "PARAGUAY"),

    # Europe
    (50, 59, -11, 2, "UK"),
    (36, 44, -10, 4, "SPAIN"),
    (42, 51, -5, 8, "FRANCE"),
    (47, 55, 5, 15, "GERMANY"),
    (36, 47, 6, 19, "ITALY"),
    (35, 42, 19, 30, "GREECE"),
    (56, 70, 4, 32, "SCANDINAVIA"),
    (49, 55, 14, 24, "POLAND"),
    (44, 49, 22, 30, "ROMANIA"),
    (36, 42, 26, 45, "TURKEY"),
    (46, 56, 22, 41, "UKRAINE"),

    # Russia (huge — split into chunks)
    (50, 72, 30, 60, "RUSSIA"),
    (50, 72, 60, 100, "RUSSIA"),
    (50, 72, 100, 140, "RUSSIA"),
    (50, 72, 140, 180, "RUSSIA"),

    # Middle East
    (12, 30, 35, 60, "MIDDLE EAST"),

    # Africa
    (22, 37, -18, 11, "N AFRICA"),
    (22, 33, 11, 35, "LIBYA/EGYPT"),
    (0, 22, -18, 16, "W AFRICA"),
    (-5, 12, 8, 32, "C AFRICA"),
    (-12, 12, 28, 42, "E AFRICA"),
    (-27, -12, 20, 41, "S AFRICA"),
    (-35, -22, 16, 33, "SOUTH AFRICA"),
    (-21, -12, 43, 51, "MADAGASCAR"),

    # Asia
    (25, 42, 44, 75, "CENTRAL ASIA"),
    (8, 35, 68, 90, "INDIA"),
    (18, 54, 97, 135, "CHINA"),
    (30, 46, 128, 146, "JAPAN"),
    (33, 43, 124, 131, "KOREA"),
    (10, 28, 93, 110, "SE ASIA"),
    (-8, 8, 95, 141, "INDONESIA"),
    (5, 20, 117, 127, "PHILIPPINES"),
    (1, 8, 100, 120, "MALAYSIA"),

    # Oceania
    (-45, -10, 112, 155, "AUSTRALIA"),
    (-48, -34, 165, 179, "NEW ZEALAND"),

    # Greenland / Iceland
    (60, 84, -55, -10, "GREENLAND"),
    (63, 67, -25, -13, "ICELAND"),

    # Oceans (catch-all, checked last)
    (0, 75, -180, -100, "N PACIFIC"),
    (-60, 0, -180, -80, "S PACIFIC"),
    (0, 75, 100, 180, "N PACIFIC"),
    (-60, 0, 100, 180, "S PACIFIC"),
    (0, 75, -100, -5, "N ATLANTIC"),
    (-60, 0, -80, 20, "S ATLANTIC"),
    (0, 75, 20, 100, "INDIAN OCN"),
    (-60, 0, 20, 100, "INDIAN OCN"),
    (-60, -45, -180, 180, "SOUTHERN OCN"),
]


def lookup(lat, lon):
    """Return region name for a lat/lon coordinate."""
    for r in REGIONS:
        if r[0] <= lat <= r[1] and r[2] <= lon <= r[3]:
            return r[4]
    return "OCEAN"
