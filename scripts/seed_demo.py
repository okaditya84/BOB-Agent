#!/usr/bin/env python3
"""Seed the BOBAI Identity Trust engine with a realistic demo scenario set.

Populates varied access events (normal logins, impossible travel, new-device fraud,
large transactions, off-hours insider actions, foreign IPs) so the analytics
dashboard at :8001/dashboard tells a compelling story immediately.

Usage:  python3 scripts/seed_demo.py [base_url]   (default http://localhost:8001)
"""

from __future__ import annotations

import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
T = 1_750_000_000  # fixed base epoch for deterministic spacing

CITIES = {
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.7041, 77.1025),
    "bengaluru": (12.9716, 77.5946),
    "ahmedabad": (23.0225, 72.5714),
    "tokyo": (35.6762, 139.6503),
    "london": (51.5074, -0.1278),
}


def post(event: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE}/v1/risk/evaluate", data=json.dumps(event).encode(),
        headers={"content-type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def ev(user, t, *, city=None, ip=None, device="home", etype="login", amount=None,
       tor=False, dc=False) -> dict:
    e = {"user_id": user, "event_type": etype, "timestamp": T + t,
         "device_fingerprint": f"{user}-{device}", "is_tor": tor, "is_datacenter": dc}
    if city:
        lat, lon = CITIES[city]
        e["geo"] = {"lat": lat, "lon": lon, "source": "client"}
    if ip:
        e["ip"] = ip
    if amount is not None:
        e["amount"] = amount
    return e


# (user, scenario) — ordered so device/location baselines build naturally.
SCENARIOS = [
    # Normal, repeated logins from home cities (become trusted -> low risk).
    ev("ravi", 0, city="mumbai"), ev("ravi", 3600, city="mumbai"),
    ev("priya", 100, city="delhi", ip="8.8.8.8"), ev("priya", 4000, city="delhi"),
    ev("anil", 200, city="bengaluru"), ev("anil", 4200, city="bengaluru"),
    ev("meena", 300, city="ahmedabad"), ev("meena", 4300, city="ahmedabad"),
    # Impossible travel: ravi Mumbai -> Tokyo 20 min later on a new device.
    ev("ravi", 4800, city="tokyo", device="phone-x"),
    # New-device + datacenter IP fraud attempt.
    ev("fraudster", 500, city="london", device="bot", dc=True, ip="45.79.0.1"),
    ev("fraudster", 700, city="london", device="bot2", tor=True),
    # Large transaction (high value) for a known user.
    ev("vikram", 800, city="mumbai"), ev("vikram", 5000, city="mumbai",
       etype="transaction", amount=750000),
    # Off-hours insider / privileged action.
    ev("insider_admin", 900, city="delhi", etype="privilege_change"),
    ev("insider_admin", 1000, city="delhi", etype="account_recovery", device="new-laptop"),
    # A couple more foreign-IP logins to populate the country breakdown.
    ev("nri_user", 1100, ip="1.1.1.1"), ev("nri_user", 5200, ip="1.1.1.1"),
]


def main() -> None:
    counts: dict[str, int] = {}
    for e in SCENARIOS:
        d = post(e)
        counts[d["action"]] = counts.get(d["action"], 0) + 1
    print(f"Seeded {len(SCENARIOS)} events -> {counts}")
    with urllib.request.urlopen(f"{BASE}/v1/analytics/summary", timeout=15) as r:
        s = json.loads(r.read())
    print(f"Dashboard now shows: {s['total_events']} events, {s['distinct_users']} users, "
          f"{s['step_up_count']} step-ups, {s['deny_count']} denied. Open {BASE}/dashboard")


if __name__ == "__main__":
    main()
