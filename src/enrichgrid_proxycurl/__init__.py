"""Proxycurl-style results from the EnrichGrid LinkedIn profile & company scraper API.

    from enrichgrid_proxycurl import Client
    client = Client()                                   # reads ENRICHGRID_KEY
    person = client.person("https://www.linkedin.com/in/some-profile")   # Proxycurl person keys, or None
    company = client.company("https://www.linkedin.com/company/some-company")

Only the fields most Proxycurl integrations read are mapped; see README for the full list and what isn't covered.
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

import requests

__all__ = ["Client", "EnrichGridError", "to_proxycurl_person", "to_proxycurl_company"]
__version__ = "0.1.0"

DEFAULT_BASE_URL = "https://enrichgrid.com"
RETRY_STATUS = {429, 503}


class EnrichGridError(Exception):
    """An API error that retrying won't fix (bad key, no credits, invalid identifier) or retries ran out."""

    def __init__(self, status: int, code: str, message: str = ""):
        super().__init__(f"{status} {code}: {message}".strip())
        self.status, self.code, self.message = status, code, message


class Client:
    """Small synchronous client: POST /v1/enrich/{kind}, polls GET /v1/lookups/{id} while the lookup is pending
    (polling is free) and retries 429/503 using Retry-After."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = DEFAULT_BASE_URL, max_wait: float = 300,
                 max_retries: int = 5, poll_interval: float = 3, session: Optional[requests.Session] = None):
        self.api_key = api_key or os.environ.get("ENRICHGRID_KEY", "")
        if not self.api_key:
            raise ValueError("Pass api_key or set ENRICHGRID_KEY (dashboard: enrichgrid.com/dashboard/keys).")
        self.base_url = base_url.rstrip("/")
        self.max_wait, self.max_retries, self.poll_interval = max_wait, max_retries, poll_interval
        self.http = session or requests.Session()
        self.http.headers.update({"x-api-key": self.api_key, "user-agent": f"enrichgrid-proxycurl/{__version__}"})

    # ------------------------------------------------------------------ raw API
    def _call(self, method: str, path: str, **kwargs) -> dict:
        last = None
        for _ in range(self.max_retries):
            r = self.http.request(method, self.base_url + path, timeout=120, **kwargs)
            try:
                body = r.json()
            except ValueError:
                body = {}
            if r.status_code in RETRY_STATUS:
                last = r
                time.sleep(min(float(r.headers.get("Retry-After") or 2), 60))
                continue
            if r.status_code >= 400:
                detail = body.get("detail") if isinstance(body, dict) else None
                detail = detail if isinstance(detail, dict) else {}
                raise EnrichGridError(r.status_code, str(detail.get("error", "error")), str(detail.get("message", "")))
            return body
        raise EnrichGridError(last.status_code if last is not None else 0, "retries_exhausted",
                              "Rate limited or temporarily unavailable; try again later. Nothing was charged.")

    def enrich(self, kind: str, identifier: str, live: bool = False) -> dict:
        """kind: "person", "company" or "school". Returns the finished EnrichGrid lookup (status done/failed)."""
        data = self._call("POST", f"/v1/enrich/{kind}", json={"identifier": identifier, "live": live})
        deadline = time.time() + self.max_wait
        while data.get("status") == "pending" and time.time() < deadline:
            time.sleep(self.poll_interval)
            data = self._call("GET", f"/v1/lookups/{data['id']}")
        return data

    # ------------------------------------------------------------------ Proxycurl-shaped helpers
    def person(self, linkedin_url: str, live: bool = False) -> Optional[dict]:
        """Proxycurl person dict, or None when the profile isn't found (Proxycurl answered 404; here it's free)."""
        data = self.enrich("person", linkedin_url, live=live)
        return to_proxycurl_person(data["profile"]) if data.get("found") and data.get("profile") else None

    def company(self, linkedin_url: str, live: bool = False) -> Optional[dict]:
        """Proxycurl company dict, or None when the company isn't found."""
        data = self.enrich("company", linkedin_url, live=live)
        return to_proxycurl_company(data["company"]) if data.get("found") and data.get("company") else None


# ---------------------------------------------------------------------- field mapping (no network)
def _date(iso: Optional[str]) -> Optional[dict]:
    """"2015-05-01" -> {"day": 1, "month": 5, "year": 2015}. When only the year is known EnrichGrid sends
    YYYY-01-01; the *_display fields show the real precision."""
    if not iso:
        return None
    year, month, day = (int(x) for x in iso.split("-"))
    return {"day": day, "month": month, "year": year}


def to_proxycurl_person(p: dict[str, Any]) -> dict[str, Any]:
    """EnrichGrid profile -> the Proxycurl person fields most integrations read."""
    sections = p.get("sections") or {}
    return {
        "public_identifier": p.get("slug"),
        "first_name": p.get("first_name"),
        "last_name": p.get("last_name"),
        "full_name": " ".join(x for x in (p.get("first_name"), p.get("last_name")) if x),
        "headline": p.get("headline"),
        "summary": p.get("summary"),
        "occupation": " at ".join(x for x in (p.get("current_title"), p.get("current_company_name")) if x),
        "country": p.get("location_country"),  # ISO code, e.g. "US"
        "city": p.get("location"),             # free text, e.g. "San Francisco Bay Area"
        "profile_pic_url": p.get("photo_url"),
        "connections": p.get("num_connections"),
        "follower_count": p.get("follower_count"),
        "experiences": [{
            "title": e.get("title"),
            "company": e.get("company_name"),
            "company_linkedin_profile_url": (f"https://www.linkedin.com/company/{e['entreprise']['slug']}/"
                                             if (e.get("entreprise") or {}).get("slug") else None),
            "description": e.get("description"),
            "location": e.get("location"),
            "starts_at": _date(e.get("started_on")),
            "ends_at": _date(e.get("ended_on")),
        } for e in sections.get("experiences") or []],
        "education": [{
            "school": ed.get("school_name"),
            "degree_name": ed.get("degree_name"),
            "field_of_study": ed.get("field_of_study"),
            "starts_at": _date(ed.get("started_on")),
            "ends_at": _date(ed.get("ended_on")),
        } for ed in sections.get("educations") or []],
        "skills": [s.get("name") for s in sections.get("skills") or []],
        "certifications": p.get("certifications") or [],
    }


def to_proxycurl_company(c: dict[str, Any]) -> dict[str, Any]:
    """EnrichGrid company -> the Proxycurl company fields most integrations read."""
    low, _, high = (c.get("staff_count_range") or "").replace("+", "-").partition("-")
    return {
        "name": c.get("name"),
        "description": c.get("description"),
        "website": c.get("website_url"),
        "industry": c.get("industry"),
        "company_size": [int(low) if low.isdigit() else None, int(high) if high.isdigit() else None],
        "company_size_on_linkedin": c.get("staff_count"),
        "founded_year": c.get("founded_year"),
        "specialities": c.get("specialties") or [],
        "follower_count": c.get("follower_count"),
        "tagline": c.get("tagline"),
        "hq": {"city": c.get("hq_city"), "state": c.get("hq_region"), "country": c.get("country_code")},
    }
