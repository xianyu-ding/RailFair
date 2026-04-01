#!/usr/bin/env python3
"""Check POST /api/predict: timetables vs single timetable (Workers vs FastAPI)."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--url",
        default="https://api.railfair.uk/api/predict",
        help="Full URL to POST /api/predict",
    )
    p.add_argument("--origin", default="EUS")
    p.add_argument("--destination", default="MAN")
    p.add_argument("--date", default="2026-04-15")
    p.add_argument("--time", default="12:00")
    args = p.parse_args()

    body = json.dumps(
        {
            "origin": args.origin,
            "destination": args.destination,
            "departure_date": args.date,
            "departure_time": args.time,
            "include_fares": True,
            "use_cache": False,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        args.url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "RailFair-verify_predict_api/1.0 (+https://railfair.uk)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode("utf-8", errors="replace")[:500])
        return 1
    except urllib.error.URLError as e:
        print("URL error:", e.reason)
        return 1

    data = json.loads(raw)
    if isinstance(data.get("data"), dict):
        data = data["data"]

    tt = data.get("timetables")
    single = data.get("timetable")
    health_hint = ""

    print("URL:", args.url)
    print("Keys (top-level payload):", sorted(data.keys()))
    print("timetables:", "missing" if tt is None else f"list len={len(tt)}")
    print("timetable (singular):", "missing" if single is None else single)

    if tt is None or (isinstance(tt, list) and len(tt) <= 1):
        sid = None
        if isinstance(tt, list) and tt:
            sid = tt[0].get("service_id")
        elif isinstance(single, dict):
            sid = single.get("service_id")
        if sid is None:
            print()
            print("Diagnosis: API returned at most one slot without service_id — typical of")
            print("Cloudflare Workers. Full NRDP lists need FastAPI (api/app.py) + timetable_parsed.json.")
            return 2

    if isinstance(tt, list) and len(tt) > 1:
        print()
        print("OK: multiple timetables — frontend can list real services (subject to its time filter).")
        return 0

    print()
    print("Single timetable row; may still be NRDP if service_id is set.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
