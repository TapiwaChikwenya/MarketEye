"""HTTP-level checks for public (unauthenticated) routes (minimal app, no full stack import)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import public

_minimal = FastAPI()
_minimal.include_router(public.router, prefix="/api/v1/public", tags=["Public"])


def test_public_search_requires_query():
    with TestClient(_minimal) as client:
        r = client.get("/api/v1/public/search")
        assert r.status_code == 422


def test_public_search_rejects_empty_query_string():
    with TestClient(_minimal) as client:
        r = client.get("/api/v1/public/search?q=")
        assert r.status_code == 422


def test_public_market_stats_ok():
    with TestClient(_minimal) as client:
        r = client.get("/api/v1/public/market-stats")
        assert r.status_code == 200
        body = r.json()
        assert "uptime" in body
        assert "total_users" in body
