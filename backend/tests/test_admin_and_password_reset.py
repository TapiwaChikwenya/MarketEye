"""Admin API and password reset flows."""
import asyncio
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.core.security import get_password_hash, create_password_reset_token, decode_password_reset_token
from app.db.base import AsyncSessionLocal


def test_password_reset_token_roundtrip():
    uid = str(uuid.uuid4())
    t = create_password_reset_token(uid)
    assert decode_password_reset_token(t) == uid
    assert decode_password_reset_token("not-a-jwt") is None


async def _seed_superuser(email: str, password: str) -> None:
    async with AsyncSessionLocal() as db:
        u = User(
            email=email,
            name="Admin Test",
            hashed_password=get_password_hash(password),
            is_active=True,
            is_superuser=True,
        )
        db.add(u)
        await db.commit()


def test_forgot_password_returns_generic_message():
    with TestClient(app) as client:
        r = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nobody@example.com"},
        )
        assert r.status_code == 200
        assert "account" in r.json()["detail"].lower()
        assert r.json().get("reset_link") is None


def test_forgot_password_dev_reset_link_for_existing_user():
    email = f"reset_{uuid.uuid4().hex[:8]}@test.com"
    pwd = "testpass123"
    with TestClient(app) as client:
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": pwd, "name": "Reset Test"},
        )
        assert reg.status_code == 201
        r = client.post("/api/v1/auth/forgot-password", json={"email": email})
        assert r.status_code == 200
        body = r.json()
        assert body.get("reset_link")
        assert "/reset-password?token=" in body["reset_link"]


def test_reset_password_invalid_token():
    with TestClient(app) as client:
        r = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "bad", "new_password": "newpass123"},
        )
        assert r.status_code == 400


def test_admin_requires_superuser():
    with TestClient(app) as client:
        r = client.get("/api/v1/admin/overview")
        assert r.status_code == 401


def test_admin_overview_and_health_as_superuser():
    email = f"admin_{uuid.uuid4().hex[:8]}@test.com"
    pwd = "testpass123"
    asyncio.run(_seed_superuser(email, pwd))

    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": pwd},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]

        r = client.get(
            "/api/v1/admin/overview",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "users_total" in data
        assert "trending_cache_hits" in data

        h = client.get(
            "/api/v1/admin/system/health",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert h.status_code == 200
        body = h.json()
        assert body["database_ok"] is True
        assert "ttl_seconds" in body
