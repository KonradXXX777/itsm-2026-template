# ai-generated: 100% - Codex added isolated endpoint, transport and instrumentation regression tests.
"""Run: python -m unittest tests.test_lab3 -v (working directory /app/src)."""
import os
import tempfile
import unittest

import httpx
from svcdesk.main import app
from svcdesk.monitoring import DURATION
from svcdesk.storage import initialize


class Lab3Tests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.old_db = os.environ.get("SVCDESK_DB")
        os.environ["SVCDESK_DB"] = self.directory.name + "/test.db"
        initialize()
        self.requests = []
        self.upstream_status = 200
        self.transport_failure = None

        def upstream(request):
            self.requests.append(request)
            if self.transport_failure:
                raise self.transport_failure
            return httpx.Response(self.upstream_status, json={"hits": [{"id": "a", "title": "unchanged", "score": 0.7}]})

        self.upstream = httpx.AsyncClient(transport=httpx.MockTransport(upstream), timeout=5.0)
        self.old_client = getattr(app.state, "kb_client", None)
        app.state.kb_client = self.upstream
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.upstream.aclose()
        app.state.kb_client = self.old_client
        if self.old_db is None:
            os.environ.pop("SVCDESK_DB", None)
        else:
            os.environ["SVCDESK_DB"] = self.old_db
        self.directory.cleanup()

    async def test_validation_never_calls_upstream(self):
        for suffix in ["", "?q=", "?q=" + "x" * 201]:
            response = await self.client.get("/kb/search" + suffix)
            self.assertEqual(response.status_code, 422)
            self.assertIsInstance(response.json()["error"], dict)
        self.assertEqual(self.requests, [])

    async def test_encoding_hits_no_cache_or_retry(self):
        query = "password & VPN/żółć + ?"
        for _ in range(2):
            response = await self.client.get("/kb/search", params={"q": query})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"query": query, "hits": [{"id": "a", "title": "unchanged", "score": 0.7}]})
        self.assertEqual(len(self.requests), 2)
        self.assertTrue(all(r.url.params["q"] == query for r in self.requests))
        self.assertTrue(all(r.method == "GET" and r.url.path == "/search" for r in self.requests))

    async def test_upstream_non200_is_502_once(self):
        for status in [301, 404, 503]:
            self.upstream_status = status
            response = await self.client.get("/kb/search?q=test")
            self.assertEqual(response.status_code, 502)
            self.assertEqual(response.json()["error"]["code"], "upstream_unavailable")
        self.assertEqual(len(self.requests), 3)

    async def test_timeout_and_connection_failure_are_502_once(self):
        for failure in [httpx.ReadTimeout("timed out"), httpx.ConnectError("offline")]:
            self.transport_failure = failure
            response = await self.client.get("/kb/search?q=test")
            self.assertEqual(response.status_code, 502)
            self.assertEqual(response.json()["error"]["code"], "upstream_unavailable")
        self.assertEqual(len(self.requests), 2)

    async def test_exactly_once_and_metrics_excluded(self):
        metric = DURATION.labels("GET", "/kb/search", "200")
        # Python client stores disjoint internal buckets; exposition makes them cumulative.
        before = metric._sum.get(), sum(bucket.get() for bucket in metric._buckets)
        await self.client.get("/kb/search?q=unique-value-not-a-label")
        self.assertGreater(metric._sum.get(), before[0])
        self.assertEqual(sum(bucket.get() for bucket in metric._buckets) - before[1], 1)
        response = await self.client.get("/metrics")
        self.assertTrue(response.headers["content-type"].startswith("text/plain"))
        self.assertNotIn("unique-value-not-a-label", response.text)
        self.assertNotIn('http_route="/metrics"', response.text)

    async def test_unknown_ids_and_paths_use_bounded_templates(self):
        for i in range(10):
            await self.client.get(f"/tickets/random-id-{i}")
            await self.client.get(f"/unknown-{i}")
        response = await self.client.get("/metrics")
        self.assertIn('http_route="/tickets/{ticket_id}"', response.text)
        self.assertIn('http_route="unmatched"', response.text)
        self.assertNotIn("random-id-", response.text)
        self.assertNotIn("unknown-", response.text)
