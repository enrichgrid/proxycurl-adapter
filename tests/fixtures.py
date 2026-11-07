"""Synthetic EnrichGrid responses (fictional person and company) shaped like the real API output."""

PERSON = {
    "slug": "jane-example-42", "first_name": "Jane", "last_name": "Example",
    "headline": "VP Sales at Example Analytics", "summary": "Builds B2B sales teams.",
    "current_title": "VP Sales", "current_company_name": "Example Analytics",
    "location": "Austin, Texas, United States", "location_country": "US",
    "photo_url": "https://example.invalid/jane.jpg", "num_connections": 812, "follower_count": 1430,
    "seniority": "vp", "job_function": "sales",
    "sections": {
        "experiences": [
            {"title": "VP Sales", "company_name": "Example Analytics", "description": "Leads a team of 20.",
             "location": "Austin, TX", "started_on": "2021-03-01", "ended_on": None, "is_current": True,
             "entreprise": {"slug": "example-analytics", "name": "Example Analytics", "staff_count": 240}},
            {"title": "Account Executive", "company_name": "Sample Soft", "description": None,
             "location": None, "started_on": "2016-01-01", "ended_on": "2021-02-01", "is_current": False,
             "entreprise": None},
        ],
        "educations": [
            {"school_name": "Example State University", "degree_name": "BBA", "field_of_study": "Marketing",
             "started_on": "2010-01-01", "ended_on": "2014-01-01"},
        ],
        "skills": [{"name": "Sales Management", "endorsement_count": 31}, {"name": "SaaS", "endorsement_count": 12}],
    },
    "certifications": [{"name": "Certified Sales Professional", "authority": "Example Institute"}],
}

COMPANY = {
    "slug": "example-analytics", "name": "Example Analytics", "description": "Analytics for revenue teams.",
    "website_url": "https://example.invalid", "industry": "Software Development", "staff_count_range": "201-500",
    "staff_count": 240, "founded_year": 2015, "specialties": ["Analytics", "B2B"], "follower_count": 5100,
    "tagline": "Know your pipeline", "hq_city": "Austin", "hq_region": "Texas", "country_code": "US",
}


def lookup(kind, record, status="done", found=True, lid="lk1"):
    out = {"id": lid, "status": status, "identifier": "x", "found": found if status == "done" else None,
           "credits_charged": 1 if found else 0, "kind": kind}
    if status == "pending":
        out["poll"] = f"/v1/lookups/{lid}"
    elif found:
        out["profile" if kind == "person" else kind] = record
    return out
