"""Run: python -m unittest discover -s tests  (no network: a fake HTTP session replays API answers)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

import enrichgrid_proxycurl as ep  # noqa: E402
from fixtures import COMPANY, PERSON, lookup  # noqa: E402


class FakeResponse:
    def __init__(self, status, body, headers=None):
        self.status_code, self._body, self.headers = status, body, headers or {}

    def json(self):
        return self._body


class FakeSession:
    """Answers requests from a queue and records them."""

    def __init__(self, answers):
        self.answers, self.calls, self.headers = list(answers), [], {}

    def request(self, method, url, timeout=None, **kwargs):
        self.calls.append((method, url, kwargs.get("json")))
        status, body, headers = self.answers.pop(0)
        return FakeResponse(status, body, headers)


def client(answers):
    return ep.Client(api_key="test-key", max_retries=3, poll_interval=0, session=FakeSession(answers))


class MappingTests(unittest.TestCase):
    def test_person_fields(self):
        p = ep.to_proxycurl_person(PERSON)
        self.assertEqual(p["public_identifier"], "jane-example-42")
        self.assertEqual(p["full_name"], "Jane Example")
        self.assertEqual(p["occupation"], "VP Sales at Example Analytics")
        self.assertEqual(p["country"], "US")
        self.assertEqual(p["connections"], 812)
        self.assertEqual(p["experiences"][0]["company_linkedin_profile_url"],
                         "https://www.linkedin.com/company/example-analytics/")
        self.assertEqual(p["experiences"][0]["starts_at"], {"day": 1, "month": 3, "year": 2021})
        self.assertIsNone(p["experiences"][0]["ends_at"])
        self.assertIsNone(p["experiences"][1]["company_linkedin_profile_url"])
        self.assertEqual(p["education"][0]["field_of_study"], "Marketing")
        self.assertEqual(p["skills"], ["Sales Management", "SaaS"])
        self.assertEqual(len(p["certifications"]), 1)

    def test_company_fields(self):
        c = ep.to_proxycurl_company(COMPANY)
        self.assertEqual(c["company_size"], [201, 500])
        self.assertEqual(c["company_size_on_linkedin"], 240)
        self.assertEqual(c["hq"], {"city": "Austin", "state": "Texas", "country": "US"})
        self.assertEqual(c["specialities"], ["Analytics", "B2B"])
        self.assertEqual(ep.to_proxycurl_company({**COMPANY, "staff_count_range": "10001+"})["company_size"], [10001, None])
        self.assertEqual(ep.to_proxycurl_company({})["company_size"], [None, None])


class ClientTests(unittest.TestCase):
    def test_pending_then_done_is_polled(self):
        c = client([(202, lookup("person", PERSON, status="pending"), {}),
                    (200, lookup("person", PERSON, status="pending"), {}),
                    (200, lookup("person", PERSON), {})])
        p = c.person("https://www.linkedin.com/in/jane-example-42")
        self.assertEqual(p["full_name"], "Jane Example")
        methods = [m for m, _, _ in c.http.calls]
        self.assertEqual(methods, ["POST", "GET", "GET"])
        self.assertTrue(c.http.calls[1][1].endswith("/v1/lookups/lk1"))

    def test_not_found_returns_none(self):
        c = client([(200, lookup("person", None, found=False), {})])
        self.assertIsNone(c.person("https://www.linkedin.com/in/nobody"))

    def test_429_is_retried(self):
        c = client([(429, {"detail": {"error": "rate_limited"}}, {"Retry-After": "0"}),
                    (200, lookup("company", COMPANY), {})])
        self.assertEqual(c.company("https://www.linkedin.com/company/example-analytics")["name"], "Example Analytics")
        self.assertEqual(len(c.http.calls), 2)

    def test_401_raises(self):
        c = client([(401, {"detail": {"error": "invalid_api_key", "message": "Invalid API key."}}, {})])
        with self.assertRaises(ep.EnrichGridError) as e:
            c.person("x")
        self.assertEqual((e.exception.status, e.exception.code), (401, "invalid_api_key"))

    def test_503_retries_exhausted(self):
        busy = (503, {"detail": {"error": "temporarily_unavailable"}}, {"Retry-After": "0"})
        c = client([busy, busy, busy])
        with self.assertRaises(ep.EnrichGridError) as e:
            c.person("x")
        self.assertEqual(e.exception.code, "retries_exhausted")

    def test_key_required(self):
        os.environ.pop("ENRICHGRID_KEY", None)
        with self.assertRaises(ValueError):
            ep.Client()


if __name__ == "__main__":
    unittest.main()
