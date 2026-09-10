"""
Postcode extraction and postcode -> city / region mapping. Fully offline.

  1. DISTRICT_OVERRIDES - outward codes where the postcode area name misleads
     (CH41 is Birkenhead on the Wirral, not Chester).
  2. AREA_MAP - postcode areas -> city, region and an approximate centroid used
     by the dashboard map. No geocoding API, no key.
"""
from __future__ import annotations

import re

POSTCODE_RE = re.compile(
    r"\b([GIR] ?0[A]{2}|"
    r"[A-PR-UWYZ][A-HK-Y]?[0-9][0-9A-HJKPS-UW]?)"
    r"\s?([0-9OI][ABD-HJLNP-UW-Z]{2})\b",
    re.IGNORECASE,
)
OUTWARD_RE = re.compile(r"^([A-Z]{1,2})([0-9][0-9A-Z]?)$")

DISTRICT_OVERRIDES = {
    **{f"CH{i}": ("Birkenhead", "North West") for i in range(41, 50)},
    **{f"CH{i}": ("Chester", "North West") for i in range(1, 9)},
    "CH60": ("Wirral", "North West"), "CH61": ("Wirral", "North West"),
    "CH62": ("Wirral", "North West"), "CH63": ("Wirral", "North West"),
    "CH64": ("Wirral", "North West"), "CH65": ("Ellesmere Port", "North West"),
    "CH66": ("Ellesmere Port", "North West"),
    **{f"TS{i}": ("Middlesbrough", "North East") for i in range(1, 9)},
    **{f"TS{i}": ("Stockton-on-Tees", "North East") for i in range(16, 24)},
    "RH1": ("Redhill", "South East"), "RH2": ("Reigate", "South East"),
    "DA1": ("Dartford", "South East"), "DA5": ("London", "London"),
    "DA6": ("London", "London"), "DA7": ("London", "London"),
    "DA8": ("London", "London"), "DA14": ("London", "London"),
    "DA15": ("London", "London"), "DA16": ("London", "London"),
    "DA17": ("London", "London"), "DA18": ("London", "London"),
    "SL0": ("London", "London"), "SL3": ("Slough", "South East"),
    **{f"SK{i}": ("Stockport", "North West") for i in range(1, 9)},
    "SK9": ("Wilmslow", "North West"), "SK10": ("Macclesfield", "North West"),
    "SK11": ("Macclesfield", "North West"),
    "BS31": ("Bristol", "South West"),
    "BA1": ("Bath", "South West"), "BA2": ("Bath", "South West"),
}

# area -> (major city, region, lat, lon)
AREA_MAP: dict[str, tuple[str, str, float, float]] = {
    "AB": ("Aberdeen", "Scotland", 57.15, -2.11),
    "AL": ("St Albans", "East of England", 51.75, -0.34),
    "B": ("Birmingham", "West Midlands", 52.48, -1.9),
    "BA": ("Bath", "South West", 51.38, -2.36),
    "BB": ("Blackburn", "North West", 53.75, -2.48),
    "BD": ("Bradford", "Yorkshire and The Humber", 53.79, -1.75),
    "BH": ("Bournemouth", "South West", 50.72, -1.88),
    "BL": ("Bolton", "North West", 53.58, -2.43),
    "BN": ("Brighton and Hove", "South East", 50.83, -0.14),
    "BR": ("London", "London", 51.4, 0.02),
    "BS": ("Bristol", "South West", 51.45, -2.59),
    "BT": ("Belfast", "Northern Ireland", 54.6, -5.93),
    "CA": ("Carlisle", "North West", 54.89, -2.94),
    "CB": ("Cambridge", "East of England", 52.21, 0.12),
    "CF": ("Cardiff", "Wales", 51.48, -3.18),
    "CH": ("Chester", "North West", 53.19, -2.89),
    "CM": ("Chelmsford", "East of England", 51.74, 0.47),
    "CO": ("Colchester", "East of England", 51.89, 0.9),
    "CR": ("London", "London", 51.37, -0.1),
    "CT": ("Canterbury", "South East", 51.28, 1.08),
    "CV": ("Coventry", "West Midlands", 52.41, -1.51),
    "CW": ("Crewe", "North West", 53.1, -2.44),
    "DA": ("Dartford", "South East", 51.44, 0.22),
    "DD": ("Dundee", "Scotland", 56.46, -2.97),
    "DE": ("Derby", "East Midlands", 52.92, -1.48),
    "DG": ("Dumfries", "Scotland", 55.07, -3.6),
    "DH": ("Durham", "North East", 54.78, -1.57),
    "DL": ("Darlington", "North East", 54.53, -1.55),
    "DN": ("Doncaster", "Yorkshire and The Humber", 53.52, -1.13),
    "DT": ("Dorchester", "South West", 50.71, -2.44),
    "DY": ("Dudley", "West Midlands", 52.51, -2.08),
    "E": ("London", "London", 51.53, -0.03),
    "EC": ("London", "London", 51.52, -0.09),
    "EH": ("Edinburgh", "Scotland", 55.95, -3.19),
    "EN": ("London", "London", 51.65, -0.08),
    "EX": ("Exeter", "South West", 50.72, -3.53),
    "FK": ("Falkirk", "Scotland", 56.0, -3.78),
    "FY": ("Blackpool", "North West", 53.82, -3.05),
    "G": ("Glasgow", "Scotland", 55.86, -4.25),
    "GL": ("Gloucester", "South West", 51.86, -2.24),
    "GU": ("Guildford", "South East", 51.24, -0.57),
    "GY": ("St Peter Port", "Channel Islands", 49.46, -2.54),
    "HA": ("London", "London", 51.58, -0.34),
    "HD": ("Huddersfield", "Yorkshire and The Humber", 53.65, -1.78),
    "HG": ("Harrogate", "Yorkshire and The Humber", 53.99, -1.54),
    "HP": ("Hemel Hempstead", "East of England", 51.75, -0.47),
    "HR": ("Hereford", "West Midlands", 52.06, -2.72),
    "HS": ("Stornoway", "Scotland", 58.21, -6.39),
    "HU": ("Kingston upon Hull", "Yorkshire and The Humber", 53.75, -0.34),
    "HX": ("Halifax", "Yorkshire and The Humber", 53.72, -1.86),
    "IG": ("London", "London", 51.56, 0.07),
    "IM": ("Douglas", "Isle of Man", 54.15, -4.48),
    "IP": ("Ipswich", "East of England", 52.06, 1.16),
    "IV": ("Inverness", "Scotland", 57.48, -4.22),
    "JE": ("St Helier", "Channel Islands", 49.19, -2.11),
    "KA": ("Kilmarnock", "Scotland", 55.61, -4.5),
    "KT": ("London", "London", 51.41, -0.3),
    "KW": ("Kirkwall", "Scotland", 58.98, -2.96),
    "KY": ("Kirkcaldy", "Scotland", 56.11, -3.16),
    "L": ("Liverpool", "North West", 53.41, -2.98),
    "LA": ("Lancaster", "North West", 54.05, -2.8),
    "LD": ("Llandrindod Wells", "Wales", 52.24, -3.38),
    "LE": ("Leicester", "East Midlands", 52.64, -1.13),
    "LL": ("Llandudno", "Wales", 53.32, -3.83),
    "LN": ("Lincoln", "East Midlands", 53.23, -0.54),
    "LS": ("Leeds", "Yorkshire and The Humber", 53.8, -1.55),
    "LU": ("Luton", "East of England", 51.88, -0.42),
    "M": ("Manchester", "North West", 53.48, -2.24),
    "ME": ("Medway", "South East", 51.39, 0.52),
    "MK": ("Milton Keynes", "South East", 52.04, -0.76),
    "ML": ("Motherwell", "Scotland", 55.79, -3.99),
    "N": ("London", "London", 51.56, -0.11),
    "NE": ("Newcastle upon Tyne", "North East", 54.98, -1.61),
    "NG": ("Nottingham", "East Midlands", 52.95, -1.15),
    "NN": ("Northampton", "East Midlands", 52.24, -0.9),
    "NP": ("Newport", "Wales", 51.58, -2.99),
    "NR": ("Norwich", "East of England", 52.63, 1.3),
    "NW": ("London", "London", 51.55, -0.19),
    "OL": ("Oldham", "North West", 53.54, -2.12),
    "OX": ("Oxford", "South East", 51.75, -1.26),
    "PA": ("Paisley", "Scotland", 55.85, -4.42),
    "PE": ("Peterborough", "East of England", 52.57, -0.24),
    "PH": ("Perth", "Scotland", 56.4, -3.44),
    "PL": ("Plymouth", "South West", 50.38, -4.14),
    "PO": ("Portsmouth", "South East", 50.82, -1.09),
    "PR": ("Preston", "North West", 53.76, -2.7),
    "RG": ("Reading", "South East", 51.45, -0.97),
    "RH": ("Crawley", "South East", 51.11, -0.19),
    "RM": ("London", "London", 51.57, 0.18),
    "S": ("Sheffield", "Yorkshire and The Humber", 53.38, -1.47),
    "SA": ("Swansea", "Wales", 51.62, -3.94),
    "SE": ("London", "London", 51.47, -0.05),
    "SG": ("Stevenage", "East of England", 51.9, -0.2),
    "SK": ("Stockport", "North West", 53.41, -2.16),
    "SL": ("Slough", "South East", 51.51, -0.59),
    "SM": ("London", "London", 51.36, -0.19),
    "SN": ("Swindon", "South West", 51.56, -1.78),
    "SO": ("Southampton", "South East", 50.91, -1.4),
    "SP": ("Salisbury", "South West", 51.07, -1.79),
    "SR": ("Sunderland", "North East", 54.91, -1.38),
    "SS": ("Southend-on-Sea", "East of England", 51.54, 0.71),
    "ST": ("Stoke-on-Trent", "West Midlands", 53.0, -2.18),
    "SW": ("London", "London", 51.46, -0.16),
    "SY": ("Shrewsbury", "West Midlands", 52.71, -2.75),
    "TA": ("Taunton", "South West", 51.02, -3.1),
    "TD": ("Galashiels", "Scotland", 55.62, -2.81),
    "TF": ("Telford", "West Midlands", 52.68, -2.45),
    "TN": ("Royal Tunbridge Wells", "South East", 51.13, 0.26),
    "TQ": ("Torquay", "South West", 50.46, -3.53),
    "TR": ("Truro", "South West", 50.26, -5.05),
    "TS": ("Middlesbrough", "North East", 54.57, -1.23),
    "TW": ("London", "London", 51.45, -0.33),
    "UB": ("London", "London", 51.53, -0.42),
    "W": ("London", "London", 51.51, -0.2),
    "WA": ("Warrington", "North West", 53.39, -2.59),
    "WC": ("London", "London", 51.52, -0.12),
    "WD": ("Watford", "East of England", 51.66, -0.4),
    "WF": ("Wakefield", "Yorkshire and The Humber", 53.68, -1.5),
    "WN": ("Wigan", "North West", 53.54, -2.63),
    "WR": ("Worcester", "West Midlands", 52.19, -2.22),
    "WS": ("Walsall", "West Midlands", 52.59, -1.98),
    "WV": ("Wolverhampton", "West Midlands", 52.59, -2.13),
    "YO": ("York", "Yorkshire and The Humber", 53.96, -1.08),
    "ZE": ("Lerwick", "Scotland", 60.15, -1.15)
}

CITY_KEYWORDS = {
    "london": "London", "birmingham": "Birmingham", "manchester": "Manchester",
    "liverpool": "Liverpool", "leeds": "Leeds", "sheffield": "Sheffield",
    "bristol": "Bristol", "newcastle": "Newcastle upon Tyne",
    "nottingham": "Nottingham", "leicester": "Leicester", "cardiff": "Cardiff",
    "glasgow": "Glasgow", "edinburgh": "Edinburgh", "belfast": "Belfast",
    "brighton": "Brighton and Hove", "southampton": "Southampton",
    "portsmouth": "Portsmouth", "coventry": "Coventry",
    "hull": "Kingston upon Hull", "bradford": "Bradford",
    "stoke": "Stoke-on-Trent", "plymouth": "Plymouth", "derby": "Derby",
    "wolverhampton": "Wolverhampton", "norwich": "Norwich", "oxford": "Oxford",
    "cambridge": "Cambridge", "york": "York", "reading": "Reading",
    "luton": "Luton", "milton keynes": "Milton Keynes",
    "birkenhead": "Birkenhead", "wirral": "Birkenhead",
}


def find_postcode(text: str) -> str:
    if not text:
        return ""
    for m in POSTCODE_RE.finditer(text):
        out, inward = m.group(1).upper(), m.group(2).upper()
        inward = inward[0].replace("O", "0").replace("I", "1") + inward[1:]
        if OUTWARD_RE.match(out):
            return f"{out} {inward}"
    return ""


def outward(postcode: str) -> str:
    return postcode.split(" ")[0].upper() if postcode else ""


def area(postcode: str) -> str:
    m = OUTWARD_RE.match(outward(postcode))
    return m.group(1).upper() if m else ""


def city_from_postcode(postcode: str) -> tuple[str, str]:
    ow = outward(postcode)
    if ow in DISTRICT_OVERRIDES:
        return DISTRICT_OVERRIDES[ow]
    a = area(postcode)
    if a in AREA_MAP:
        city, region, _, _ = AREA_MAP[a]
        return city, region
    return "", ""


def city_from_address(address: str) -> str:
    low = (address or "").lower()
    for key, city in CITY_KEYWORDS.items():
        if key in low:
            return city
    return ""


def latlon(postcode: str):
    a = area(postcode)
    if a in AREA_MAP:
        _, _, lat, lon = AREA_MAP[a]
        return lat, lon
    return None, None


def resolve(address: str, fallback_text: str = "") -> dict:
    pc = find_postcode(address) or find_postcode(fallback_text)
    city, region = city_from_postcode(pc)
    if not city:
        city = city_from_address(address) or city_from_address(fallback_text)
    lat, lon = latlon(pc)
    return {"postcode": pc, "postcode_outward": outward(pc), "postcode_area": area(pc),
            "city": city, "region": region, "lat": lat, "lon": lon}
