#!/usr/bin/env python3
"""
Count NRDP services for origin/destination/date using the same filters as
api/app.py get_timetables_for_date (CRS match, validity dates, weekday, Oct 2025 threshold).

Usage (from repo root):
  python3 check_nrdp_od_date.py EUS MAN 2026-04-15
  python3 check_nrdp_od_date.py KGX EDB 2026-04-15 --json-path /path/to/timetable_parsed.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from api.crs_tiploc import location_codes_for_query
DEFAULT_JSON = REPO_ROOT / "data" / "timetable_parsed.json"
MIN_THRESHOLD_DATE = datetime(2025, 10, 1).date()
DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def nrdp_row_to_departure_iso(nrdp_service: dict, dep_date) -> str | None:
    origin_time_str = nrdp_service.get("origin_time")
    dest_time_str = nrdp_service.get("destination_time")
    if not origin_time_str or not dest_time_str:
        return None
    try:
        parts = origin_time_str.split(":")
        origin_time = time(
            int(parts[0]),
            int(parts[1]),
            int(parts[2]) if len(parts) > 2 else 0,
        )
    except (ValueError, IndexError):
        return None
    dep_dt = datetime.combine(dep_date, origin_time)
    return dep_dt.isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Count NRDP timetable rows matching OD + date (API-equivalent filters)."
    )
    parser.add_argument("origin", help="Origin CRS, e.g. EUS")
    parser.add_argument("destination", help="Destination CRS, e.g. MAN")
    parser.add_argument("date", help="Departure date YYYY-MM-DD")
    parser.add_argument(
        "--json-path",
        type=Path,
        default=DEFAULT_JSON,
        help=f"Path to timetable_parsed.json (default: {DEFAULT_JSON})",
    )
    parser.add_argument(
        "--list",
        type=int,
        default=0,
        metavar="N",
        help="Print first N departures (ISO) after sorting",
    )
    args = parser.parse_args()

    origin = args.origin.upper().strip()
    dest = args.destination.upper().strip()
    dep_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    query_day = DAY_NAMES[dep_date.weekday()]

    path = args.json_path
    if not path.is_file():
        print(f"Missing file: {path}")
        print(
            "timetable_parsed.json is usually under data/ and may be gitignored; "
            "generate or copy it before running this check."
        )
        return 1

    with open(path, "r", encoding="utf-8") as f:
        nrdp_data = json.load(f)

    data_dir = path.parent
    origin_codes = set(location_codes_for_query(origin, data_dir))
    dest_codes = set(location_codes_for_query(dest, data_dir))

    matching_services: list[dict] = []
    for s in nrdp_data.get("services", []):
        if s.get("origin_location") not in origin_codes or s.get("destination_location") not in dest_codes:
            continue

        svc_end = s.get("end_date")
        if svc_end:
            try:
                if datetime.strptime(svc_end, "%Y-%m-%d").date() < MIN_THRESHOLD_DATE:
                    continue
            except ValueError:
                pass

        svc_start = s.get("start_date")
        if svc_start:
            try:
                if dep_date < datetime.strptime(svc_start, "%Y-%m-%d").date():
                    continue
            except ValueError:
                pass

        if svc_end:
            try:
                if dep_date > datetime.strptime(svc_end, "%Y-%m-%d").date():
                    continue
            except ValueError:
                pass

        days_run = s.get("days_run", [])
        if days_run and query_day not in days_run:
            continue

        matching_services.append(s)

    timetables: list[tuple[str, str]] = []
    for svc in matching_services:
        dep_iso = nrdp_row_to_departure_iso(svc, dep_date)
        if not dep_iso:
            continue
        uid = str(svc.get("train_uid", "unknown"))
        timetables.append((dep_iso, uid))

    timetables.sort(key=lambda x: x[0])
    seen = set()
    unique_slots: list[tuple[str, str]] = []
    for dep_iso, uid in timetables:
        key = (uid, dep_iso)
        if key in seen:
            continue
        seen.add(key)
        unique_slots.append((dep_iso, uid))

    print(f"File: {path}")
    print(f"Query: {origin} -> {dest} on {args.date} ({query_day})")
    print(f"NRDP location codes (CRS + TIPLOC aliases): origin {sorted(origin_codes)}, dest {sorted(dest_codes)}")
    print(f"Matching NRDP rows (after CRS/date/weekday filters): {len(matching_services)}")
    print(f"Rows with valid origin/destination times: {len(timetables)}")
    print(f"Unique (train_uid, scheduled_departure) slots: {len(unique_slots)}")
    print()
    print("If unique slots is 1 but you expect many trains, the NRDP extract may only")
    print("contain one pattern for this OD, or CRS codes may not match the file.")
    print("If the API returns more than the UI shows, check the frontend time window (±2h) and 'Show all'.")
    if len(matching_services) == 0:
        print()
        print("Hint: if still 0, add CRS→TIPLOC entries in data/crs_to_tiploc.json or api/crs_tiploc.py,")
        print("or run check_nrdp_routes.py to see (origin_location, destination_location) pairs in the file.")

    n_list = args.list
    if n_list > 0 and unique_slots:
        print(f"\nFirst {min(n_list, len(unique_slots))} departures:")
        for dep_iso, uid in unique_slots[:n_list]:
            print(f"  {dep_iso}  train_uid={uid}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
