# Approximate lat/lng for Florida toll plazas based on road + location name.
# Plazas on the same road at the same mile post but different directions
# share the same coordinates — they're essentially the same physical location.

PLAZA_COORDINATES: dict[str, tuple[float, float]] = {
    # SR-91 Florida's Turnpike (south to north by mile post)
    "SR91 GOLDEN GLADES": (25.9125, -80.2005),
    "SR91 DOLPHIN CENTER": (25.9200, -80.2100),
    "SR91 POMPANO BCH": (26.2350, -80.1750),
    "SR91 POMPANO COCONUT CK": (26.2500, -80.1780),
    "SR91 GLADES RD": (26.3680, -80.1300),
    "SR91 ATLANTIC AV": (26.4550, -80.1050),
    "SR91 LANTANA": (26.5860, -80.0720),
    "SR91 FOREST H BLV": (26.6400, -80.0700),
    "SR91 BELVEDERE RD": (26.6650, -80.0700),
    "SR91 45TH STREET": (26.7150, -80.0750),
    "SR91 PGA BLVD": (26.8350, -80.1100),
    "SR91 JUPITER": (26.9200, -80.1350),
    "SR91 STUART": (27.1050, -80.2200),
    "SR91 BECKER RD": (27.2350, -80.2900),
    "SR91 PT ST LUCIE": (27.2900, -80.3100),
    "SR91 MIDWAY RD": (27.4600, -80.3900),
    "SR91 FT PIERCE": (27.4100, -80.3500),
    "SR91 THREE LAKES": (28.2300, -81.3400),
    "SR91 LEESBURG": (28.7500, -81.7500),

    # SR-869 Sawgrass Expressway (south to north by mile post)
    "SR869 SUNRISE": (26.1560, -80.3300),
    "SR869 OAKLAND PK BL": (26.1750, -80.3200),
    "SR869 SR7 US441": (26.3350, -80.2350),
    "SR869 LYONS RD": (26.3450, -80.2250),
    "SR869 DEERFIELD": (26.3620, -80.1800),

    # I-75 (south to north by mile post)
    "I-75 MIAMI GARDENS": (25.9400, -80.3100),
    "I-75 MIRAMAR": (25.9750, -80.3200),
    "I-75 PINES": (26.0100, -80.3300),
    "I-75 GRIFFIN": (26.0550, -80.3400),

    # I-95 (south to north by mile post)
    "I-95 NW 54 ST": (25.8300, -80.2050),
    "I-95 NW 144 ST": (25.9050, -80.2100),
    "I-95 MIAMIGARDENS": (25.9450, -80.2100),
    "I-95 SR 824": (26.0200, -80.1700),

    # I-595
    "I-595 FLAMINGO RD": (26.1200, -80.3200),

    # SR-924 Gratigny Parkway
    "SR 924 EAST (42ND AVE)": (25.9200, -80.2700),
    "SR 924 EAST (57TH AVE)": (25.9200, -80.2500),
    "SR 924 WEST (42ND AVE)": (25.9200, -80.2700),
    "SR 924 WEST (57TH AVE)": (25.9200, -80.2500),

    # SR-417 Central Florida GreeneWay
    "SR 417 BOGGY CREEK": (28.3900, -81.3000),
    "SR 417 COLONIAL": (28.5500, -81.2500),
    "SR 417 CURRY FORD": (28.5100, -81.2700),

    # SR-408 East-West Expressway
    "SR 408 DEAN": (28.5450, -81.3300),

    # SR-528 Beachline
    "SR 528 BEACHLINE": (28.4300, -81.1500),
    "SR 528 DALLAS": (28.4200, -81.0500),
    "SR528 BCHLIN E SR520": (28.4000, -80.7500),

    # SR-112
    "SR112 EAST (17TH AVE)": (25.7950, -80.2250),
}


def get_plaza_coords(plaza_name: str) -> tuple[float, float] | None:
    """Look up coordinates for a plaza name.

    Matches by stripping direction (NB/SB/EB/WB) and suffix details
    to find the base location.
    """
    if not plaza_name:
        return None

    # Direct match first
    if plaza_name in PLAZA_COORDINATES:
        return PLAZA_COORDINATES[plaza_name]

    # Strip direction indicators and mile post suffixes to match base name
    import re
    # Remove direction + "ON"/"OFF" + mile post at end
    cleaned = re.sub(r"\s+(NB|SB|EB|WB)\s*(ON|OFF|MAIN|EXLN)?\s*(MP\s*\d+)?$", "", plaza_name).strip()
    if cleaned in PLAZA_COORDINATES:
        return PLAZA_COORDINATES[cleaned]

    # Try removing A/B variants (e.g., "DEERFIELD A" -> "DEERFIELD")
    cleaned2 = re.sub(r"\s+[AB]\s*$", "", cleaned).strip()
    if cleaned2 in PLAZA_COORDINATES:
        return PLAZA_COORDINATES[cleaned2]

    # Try without trailing details after last known road marker
    for key in PLAZA_COORDINATES:
        if plaza_name.startswith(key):
            return PLAZA_COORDINATES[key]

    return None
