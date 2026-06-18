"""Optional IP -> gelocation enrichment via a MaxMind/DB-IP .mmdb database.

Browser-provided geolocation (with consent) is the primary signal; this fills in
country/city/coordinates from the IP when no precise location is supplied. Degrades
gracefully to a no-op if the database file is absent.
"""

from __future__ import annotations


class GeoIP:
    def __init__(self, mmdb_path: str | None) -> None:
        self._reader = None
        if mmdb_path:
            try:
                import geoip2.database

                self._reader = geoip2.database.Reader(mmdb_path)
            except Exception:
                self._reader = None

    @property
    def available(self) -> bool:
        return self._reader is not None

    def lookup(self, ip: str | None) -> dict | None:
        if not ip or self._reader is None:
            return None
        try:
            r = self._reader.city(ip)
            return {
                "lat": r.location.latitude,
                "lon": r.location.longitude,
                "country": r.country.name,
                "city": r.city.name,
            }
        except Exception:
            return None

    def close(self) -> None:
        if self._reader is not None:
            self._reader.close()
