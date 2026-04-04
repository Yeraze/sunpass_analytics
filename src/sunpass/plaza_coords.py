# GPS coordinates for Florida toll plazas, derived from cross-street
# intersections with each highway and verified mile-post spacing.
# Plazas on the same road at the same mile post but different directions
# share the same coordinates — they're the same physical gantry.

PLAZA_COORDINATES: dict[str, tuple[float, float]] = {
    # SR-91 Florida's Turnpike — HEFT (south of Golden Glades)
    "SR91 DOLPHIN CENTER": (25.7950, -80.2680),

    # SR-91 Florida's Turnpike — mainline (MP0 at Golden Glades, north)
    "SR91 GOLDEN GLADES": (25.9300, -80.2107),
    "SR91 POMPANO BCH": (26.2224, -80.1857),
    "SR91 POMPANO COCONUT CK": (26.2452, -80.1674),
    "SR91 GLADES RD": (26.3697, -80.1628),
    "SR91 ATLANTIC AV": (26.4555, -80.1746),
    "SR91 BOYNTON BCH BV": (26.5280, -80.1726),
    "SR91 LANTANA": (26.5631, -80.1731),
    "SR91 FOREST H BLV": (26.6430, -80.1570),
    "SR91 BELVEDERE RD": (26.6682, -80.1495),
    "SR91 45TH STREET": (26.7233, -80.1280),
    "SR91 PGA BLVD": (26.8394, -80.1272),
    "SR91 JUPITER": (26.9348, -80.1538),
    "SR91 STUART": (27.1577, -80.3021),
    "SR91 BECKER RD": (27.2095, -80.3337),
    "SR91 PT ST LUCIE": (27.2508, -80.3479),
    "SR91 MIDWAY RD": (27.3530, -80.3940),
    "SR91 FT PIERCE": (27.4222, -80.4094),
    "SR91 THREE LAKES": (28.1817, -81.3032),
    "SR91 LEESBURG": (28.6660, -81.8348),

    # SR-869 Sawgrass Expressway (MP1 south at I-75, northeast to I-95)
    "SR869 SUNRISE": (26.1566, -80.3323),
    "SR869 OAKLAND PK BL": (26.1700, -80.3170),
    "SR869 SR7 US441": (26.2999, -80.2024),
    "SR869 LYONS RD": (26.3150, -80.2110),
    "SR869 DEERFIELD": (26.3175, -80.1816),

    # I-75 Express lanes (south to north through Broward)
    "I-75 MIAMI GARDENS": (25.9420, -80.3200),
    "I-75 MIRAMAR": (25.9730, -80.3130),
    "I-75 PINES": (26.0020, -80.2950),
    "I-75 GRIFFIN": (26.0560, -80.2690),

    # I-95 Express lanes (south to north through Miami-Dade/Broward)
    "I-95 NW 54 ST": (25.8230, -80.2060),
    "I-95 NW 144 ST": (25.9050, -80.2100),
    "I-95 MIAMIGARDENS": (25.9360, -80.2170),
    "I-95 SR 824": (26.0130, -80.1860),

    # I-595 (east-west through Broward)
    "I-595 FLAMINGO RD": (26.1210, -80.3216),

    # SR-924 Gratigny Parkway (east-west along NW 119th St)
    "SR 924 EAST (42ND AVE)": (25.8838, -80.2588),
    "SR 924 EAST (57TH AVE)": (25.8838, -80.2815),
    "SR 924 WEST (42ND AVE)": (25.8838, -80.2588),
    "SR 924 WEST (57TH AVE)": (25.8838, -80.2815),

    # SR-417 Central Florida GreeneWay (south to north, Orlando area)
    "SR 417 BOGGY CREEK": (28.3676, -81.3354),
    "SR 417 CURRY FORD": (28.5210, -81.2627),
    "SR 417 COLONIAL": (28.5520, -81.2475),

    # SR-408 East-West Expressway (Orlando)
    "SR 408 DEAN": (28.5469, -81.2346),

    # SR-528 Beachline Expressway (Orlando toward coast)
    "SR 528 BEACHLINE": (28.4516, -81.2095),
    "SR 528 DALLAS": (28.4516, -81.0951),
    "SR528 BCHLIN E SR520": (28.4525, -80.9791),

    # SR-112 Airport Expressway (Miami)
    "SR112 EAST (17TH AVE)": (25.7957, -80.2342),
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
