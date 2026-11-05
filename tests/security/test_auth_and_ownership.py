"""
Security regression tests (production-readiness plan, Phase 0).

Exercised through the real HTTP stack (TestClient) so dependency injection,
validation, middleware and auth headers are all covered.
"""
import hashlib
import os
import tempfile
import uuid

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/security.db")
os.environ.setdefault("UPLOAD_DIR", os.path.join(tempfile.mkdtemp(), "uploads"))

import pytest
from fastapi.testclient import TestClient

from backend.app.config.settings import settings
from backend.app.core.rate_limit import reset_rate_limits
from backend.app.db.database import SessionLocal
from backend.app.main import app
from backend.app.models.user import User

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


@pytest.fixture(scope="module")
def client():
    previous = settings.RATE_LIMIT_ENABLED
    settings.RATE_LIMIT_ENABLED = False
    with TestClient(app) as c:
        yield c
    settings.RATE_LIMIT_ENABLED = previous


def _register(client, password="correct-horse-battery"):
    suffix = uuid.uuid4().hex[:8]
    r = client.post("/auth/register", json={
        "email": f"u{suffix}@example.com", "username": f"user_{suffix}", "password": password,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    return {"Authorization": f"Bearer {body['token']}"}, body["user"]


@pytest.fixture()
def alice(client):
    return _register(client)


@pytest.fixture()
def bob(client):
    return _register(client)


# ── Authentication ───────────────────────────────────────────────────────────

def test_weak_password_rejected(client):
    r = client.post("/auth/register", json={"email": "w@example.com", "username": "weakling", "password": "short"})
    assert r.status_code == 422


def test_token_is_signed_jwt(alice):
    headers, _ = alice
    assert headers["Authorization"].split(" ", 1)[1].count(".") == 2


def test_forged_legacy_token_rejected(client, alice):
    _, user = alice
    forged = {"Authorization": f"Bearer yatra_{user['id']}_deadbeef"}
    assert client.get("/auth/me", headers=forged).json()["is_authenticated"] is False
    assert client.get("/itineraries", headers=forged).status_code == 401


def test_tampered_jwt_rejected(client, alice):
    headers, _ = alice
    token = headers["Authorization"].split(" ", 1)[1]
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    assert client.get("/itineraries", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401


def test_login_wrong_password(client, alice):
    _, user = alice
    r = client.post("/auth/login", json={"username_or_email": user["username"], "password": "nope-nope-nope"})
    assert r.status_code == 401


def test_legacy_sha256_hash_is_accepted_and_upgraded(client):
    db = SessionLocal()
    name = f"legacy_{uuid.uuid4().hex[:8]}"
    legacy = hashlib.sha256(b"legacy-pass-123yatrasathi_nepal_secret_salt_2026").hexdigest()
    db.add(User(id=uuid.uuid4(), email=f"{name}@example.com", username=name, hashed_password=legacy))
    db.commit()

    r = client.post("/auth/login", json={"username_or_email": name, "password": "legacy-pass-123"})
    assert r.status_code == 200

    db.expire_all()
    assert db.query(User).filter_by(username=name).first().hashed_password.startswith("$2")
    db.close()


def test_guest_upgrade_requires_token_and_only_upgrades_guests(client, alice):
    payload = lambda: {"email": f"g{uuid.uuid4().hex[:8]}@example.com",
                       "username": f"g_{uuid.uuid4().hex[:8]}", "password": "correct-horse-3"}
    assert client.post("/auth/upgrade", json=payload()).status_code == 401

    guest = client.post("/auth/guest").json()
    assert guest["user"]["is_guest"] is True
    r = client.post("/auth/upgrade", headers={"Authorization": f"Bearer {guest['token']}"}, json=payload())
    assert r.status_code == 200 and r.json()["user"]["is_guest"] is False

    # A registered (non-guest) account cannot be taken over via /upgrade.
    headers, _ = alice
    assert client.post("/auth/upgrade", headers=headers, json=payload()).status_code == 400


# ── Ownership: itineraries ───────────────────────────────────────────────────

def test_itinerary_ownership(client, alice, bob):
    A, a_user = alice
    B, _ = bob

    assert client.post("/itineraries", json={"title": "x", "itinerary_data": {}}).status_code == 401

    r = client.post("/itineraries", headers=A, json={"title": "Alice trip", "itinerary_data": {"summary": "s"}})
    assert r.status_code == 200
    it_id, share_id = r.json()["itinerary_id"], r.json()["share_id"]

    assert [i["id"] for i in client.get("/itineraries", headers=A).json()["itineraries"]] == [it_id]
    assert client.get("/itineraries", headers=B).json()["itineraries"] == []
    assert client.get(f"/itineraries?user_id={a_user['id']}", headers=B).json()["itineraries"] == []
    assert client.get("/itineraries").status_code == 401

    assert client.get(f"/itineraries/{it_id}", headers=B).status_code == 404
    assert client.delete(f"/itineraries/{it_id}", headers=B).status_code == 404
    assert client.delete(f"/itineraries/{it_id}").status_code == 401

    assert client.get(f"/itineraries/share/{share_id}").status_code == 200
    assert client.delete(f"/itineraries/{it_id}", headers=A).status_code == 200


# ── Ownership: memories ──────────────────────────────────────────────────────

def test_memory_ownership_and_validation(client, alice, bob):
    A, _ = alice
    B, _ = bob
    body = {"place_name": "Pokhara", "image_url": "https://example.com/y.jpg"}

    assert client.post("/memories", json=body).status_code == 401
    assert client.post("/memories", headers=A, json={**body, "image_url": "data:image/png;base64,AAAA"}).status_code == 422

    r = client.post("/memories", headers=A, json=body)
    assert r.status_code == 200
    m_id = r.json()["memory"]["id"]

    feed = client.get("/memories").json()["memories"]
    assert any(m["id"] == m_id for m in feed)
    assert all("user_id" not in m for m in feed)
    assert all(m["id"] != m_id for m in client.get("/memories?mine=true", headers=B).json()["memories"])

    assert client.delete(f"/memories/{m_id}", headers=B).status_code == 404
    assert client.delete(f"/memories/{m_id}", headers=A).status_code == 200


# ── Uploads ──────────────────────────────────────────────────────────────────

def test_upload_requires_auth_and_enforces_size(client, alice):
    A, _ = alice
    assert client.post("/uploads/photo", files={"file": ("a.png", PNG, "image/png")}).status_code == 401
    assert client.post("/uploads/photo", headers=A, files={"file": ("a.png", PNG, "image/png")}).status_code == 200

    big = b"\x89PNG\r\n\x1a\n" + b"0" * (settings.MAX_UPLOAD_SIZE_BYTES + 1024)
    assert client.post("/uploads/photo", headers=A, files={"file": ("big.png", big, "image/png")}).status_code == 413


# ── AI sessions ──────────────────────────────────────────────────────────────

def test_ai_requires_auth_and_sessions_are_per_user(client, bob):
    B, _ = bob
    assert client.post("/ai/chat", json={"session_id": "s", "message": "hi"}).status_code == 401
    assert client.get("/ai/sessions/web_session_user", headers=B).status_code == 404


# ── Input bounds ─────────────────────────────────────────────────────────────

def test_recommend_input_bounds(client):
    r = client.post("/recommend", json={"origin_lat": 27.7, "origin_lng": 85.3,
                                        "dest_lat": 28.2, "dest_lng": 83.9, "num_days": 10000})
    assert r.status_code == 422


def test_route_input_validation(client):
    assert client.post("/route", json={"waypoints": [[1]]}).status_code == 422
    assert client.post("/route", json={"origin_lat": 1, "origin_lng": 1, "dest_lat": 2, "dest_lng": 2,
                                       "profile": "../../x"}).status_code == 422


# ── Health ───────────────────────────────────────────────────────────────────

def test_health_endpoints(client):
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").json()["database"] == "up"
    assert "visibility_percent" not in client.get("/telemetry").json()


# ── Rate limiting ────────────────────────────────────────────────────────────

def test_auth_rate_limit(client):
    settings.RATE_LIMIT_ENABLED = True
    reset_rate_limits()
    try:
        codes = [client.post("/auth/login", json={"username_or_email": "nobody", "password": "x"}).status_code
                 for _ in range(12)]
        assert 429 in codes
    finally:
        settings.RATE_LIMIT_ENABLED = False
        reset_rate_limits()
