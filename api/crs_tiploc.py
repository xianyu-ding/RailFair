"""
Map 3-letter CRS codes to NRDP timetable location codes (TIPLOC-style strings)
as used in timetable_parsed.json (origin_location / destination_location).

The timetable file does not use CRS; without this mapping, queries like EUS→MAN
match zero rows. Optional JSON at data/crs_to_tiploc.json merges/overrides.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Verified against data/timetable_parsed.json where possible.
_DEFAULT: Dict[str, List[str]] = {
    "EUS": ["EUSTON"],
    "MAN": ["MNCRPIC"],
    "MCV": ["MNCRVIC"],
    "MIA": ["MNCRIAP"],
    "KGX": ["KNGX"],
    "PAD": ["PADTON"],
    "STP": ["STPX"],
    "MYB": ["MARYLBN"],
    "VIC": ["VICTRIC"],
    "CHX": ["CHRX"],
    "BHM": ["BHAMNWS"],
    "BMO": ["BHAMMRS"],
    "EDB": ["EDINBUR"],
    "GLC": ["GLGC"],
    "NCL": ["NWCSTLE"],
    "LDS": ["LEEDS"],
    "BRI": ["BRSTLTM"],
    "LIV": ["LVRPLSH"],
    "SHF": ["SHEFFLD"],
    "YRK": ["YORK"],
    "RDG": ["RDNGSTN"],
    "OXF": ["OXFD"],
    "CBG": ["CAMBDGE"],
    "BTN": ["BRGHTN"],
    "GTW": ["GTWK"],
    "SOU": ["SOTON"],
    "PLY": ["PLYMTH"],
    "SWA": ["SWANSEA"],
    "CDF": ["CARDFQS"],
    "NOT": ["NTNG"],
    "EXE": ["EXETRSD"],
    "COV": ["COVNTRY"],
    "CRE": ["CREWE"],
    "PRL": ["PRST"],
    "CAR": ["CARLILE"],
    "SOT": ["STFD"],
    "CLJ": ["CLPHMJW"],
    "EPS": ["EPSM"],
    "BWK": ["NBERWCK"],
    "STO": ["STOKEOT"],
    "DON": ["DONC"],
}

_cache: Optional[Dict[str, List[str]]] = None
_cache_dir: Optional[Path] = None


def _merge_file(data_dir: Path, base: Dict[str, List[str]]) -> Dict[str, List[str]]:
    out = {k: list(v) for k, v in base.items()}
    path = data_dir / "crs_to_tiploc.json"
    if not path.is_file():
        return out
    try:
        with open(path, "r", encoding="utf-8") as f:
            extra = json.load(f)
        for key, val in extra.items():
            if str(key).startswith("_"):
                continue
            if not isinstance(val, list):
                continue
            codes = [str(x).upper().strip() for x in val if x]
            if codes:
                out[str(key).upper().strip()] = codes
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Could not load crs_to_tiploc.json: %s", e)
    return out


def crs_tiploc_map(data_dir: Path) -> Dict[str, List[str]]:
    """CRS -> list of NRDP location codes to try (CRS itself is never removed)."""
    global _cache, _cache_dir
    data_dir = data_dir.resolve()
    if _cache is not None and _cache_dir == data_dir:
        return _cache
    _cache = _merge_file(data_dir, _DEFAULT)
    _cache_dir = data_dir
    return _cache


def location_codes_for_query(crs: str, data_dir: Path) -> List[str]:
    """
    Ordered list: user CRS first, then mapped TIPLOC aliases (deduped).
    """
    c = crs.upper().strip()
    codes: List[str] = [c]
    m = crs_tiploc_map(data_dir)
    for alt in m.get(c, []):
        if alt not in codes:
            codes.append(alt)
    return codes


def reset_crs_tiploc_cache() -> None:
    """For tests."""
    global _cache, _cache_dir
    _cache = None
    _cache_dir = None
