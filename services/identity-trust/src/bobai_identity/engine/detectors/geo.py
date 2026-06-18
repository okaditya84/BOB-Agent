"""Impossible-travel / geo-velocity detector.

Compares the event location against the user's last known location and the time
elapsed. An implied speed faster than `impossible_travel_kmh` is physically
impossible and is a classic account-takeover signal.
"""

from __future__ import annotations

from haversine import haversine

from ...config import Settings
from ...schemas import AuthEvent
from ...store.db import UserProfile
from . import DetectorResult


def detect(event: AuthEvent, profile: UserProfile, settings: Settings) -> DetectorResult | None:
    if event.geo is None or profile.last_lat is None or profile.last_ts is None:
        return None  # not enough history/data to judge travel

    dt_seconds = event.timestamp - profile.last_ts
    if dt_seconds <= 0:
        return None

    dist_km = haversine((profile.last_lat, profile.last_lon), (event.geo.lat, event.geo.lon))
    if dist_km < 1.0:
        return DetectorResult(0.0, "Location effectively unchanged.", {"distance_km": round(dist_km, 2)})

    hours = max(dt_seconds, settings.min_travel_seconds) / 3600.0
    speed_kmh = dist_km / hours
    raw = min(1.0, speed_kmh / settings.impossible_travel_kmh)

    data = {
        "distance_km": round(dist_km, 1),
        "elapsed_hours": round(dt_seconds / 3600.0, 2),
        "implied_speed_kmh": round(speed_kmh, 0),
        "threshold_kmh": settings.impossible_travel_kmh,
    }
    if speed_kmh >= settings.impossible_travel_kmh:
        detail = (
            f"Impossible travel: {dist_km:.0f} km in {dt_seconds / 3600.0:.1f} h "
            f"(~{speed_kmh:.0f} km/h) exceeds plausible speed."
        )
    else:
        detail = f"Location changed {dist_km:.0f} km (~{speed_kmh:.0f} km/h) since last activity."
    return DetectorResult(raw, detail, data)
