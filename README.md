# enrichgrid-proxycurl

**Proxycurl-style results from the EnrichGrid LinkedIn profile & company scraper API.**
Proxycurl shut down in July 2025. If your code reads Proxycurl fields (`public_identifier`, `occupation`, `experiences[].starts_at`, `company_size`, `hq`…), this adapter returns those keys from [EnrichGrid](https://enrichgrid.com/?ref=github-adapter), so the rest of your code can stay as it is.

- No LinkedIn login or cookies: you send a LinkedIn URL, slug or ID and get JSON back.
- 1 credit per found profile or company. Not-found lookups are free.
- Slow profiles return `pending`. The client polls for free and retries 429/503 using `Retry-After`.

## Install

```bash
pip install "git+https://github.com/enrichgrid/proxycurl-adapter@v0.1.0"
```

You can also copy `src/enrichgrid_proxycurl/__init__.py` into your project. It's one file, and its only dependency is `requests`.

## Use

```python
from enrichgrid_proxycurl import Client

client = Client()  # reads ENRICHGRID_KEY; get a key at https://enrichgrid.com/dashboard/keys (50 free credits)

person = client.person("https://www.linkedin.com/in/some-profile")
if person is None:
    print("not found (no credit charged)")
else:
    print(person["full_name"], "-", person["occupation"])
    for job in person["experiences"]:
        print(job["title"], job["company"], job["starts_at"])

company = client.company("https://www.linkedin.com/company/some-company")
print(company["company_size"], company["hq"])
```

Already have EnrichGrid JSON? The mapping functions work offline:

```python
from enrichgrid_proxycurl import to_proxycurl_person, to_proxycurl_company
legacy = to_proxycurl_person(enrichgrid_response["profile"])
```

## Field mapping

| Proxycurl | EnrichGrid source |
|---|---|
| `public_identifier` | `slug` |
| `first_name`, `last_name`, `full_name` | `first_name`, `last_name` (joined) |
| `headline`, `summary` | `headline`, `summary` |
| `occupation` | `current_title` + " at " + `current_company_name` |
| `country`, `city` | `location_country` (ISO code), `location` (free text) |
| `profile_pic_url` | `photo_url` |
| `connections`, `follower_count` | `num_connections`, `follower_count` |
| `experiences[]` | `sections.experiences[]`, plus `company_linkedin_profile_url` from the employer slug |
| `education[]` | `sections.educations[]` |
| `skills[]` | `sections.skills[].name` |
| `certifications[]` | `certifications[]` |
| company `company_size` `[min, max]` | `staff_count_range` (`"10001+"` → `[10001, None]`) |
| company `hq {city, state, country}` | `hq_city`, `hq_region`, `country_code` |
| company `website`, `specialities`, `tagline`, `founded_year` | `website_url`, `specialties`, `tagline`, `founded_year` |

## What doesn't carry over

- No emails or phone numbers. EnrichGrid returns professional data only.
- No Proxycurl "employee listing" endpoint. Use EnrichGrid people search with a company filter instead.
- The response is mapped to the most-used Proxycurl keys. It isn't a byte-for-byte clone of every Proxycurl field.
- Dates: when only the year is known, EnrichGrid sends `YYYY-01-01`, so `starts_at` shows day 1 and month 1. The raw lookup's `*_display` fields show the real precision.

Full migration guide (endpoints, Node.js, search filters): https://enrichgrid.com/guides/proxycurl-migration

## Tests

```bash
pip install requests
python -m unittest discover -s tests -v
```

The tests use synthetic data and a fake HTTP session: no network, no credits.

## License

MIT. EnrichGrid is independent and not affiliated with LinkedIn or Proxycurl/Nubela.
