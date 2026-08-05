import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.seed.demo_data import seed_demo_data


@pytest.mark.asyncio
async def test_auth_flow(test_engine):
    # Seed demo data into test DB
    await seed_demo_data()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test Login Failure
        response = await ac.post(
            "/api/v1/auth/login",
            json={"email": "owner@smsos.in", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHORIZED"

        # Test Protected Route Without Token
        response = await ac.get("/api/v1/orders")
        assert response.status_code == 401

        # Test Login Success
        response = await ac.post(
            "/api/v1/auth/login",
            json={"email": "owner@smsos.in", "password": "admin123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["role"] == "owner"

        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Test Protected Route With Valid Token
        response = await ac.get("/api/v1/orders", headers=headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_register_flow(test_engine):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test Weak Password Rejection
        resp = await ac.post(
            "/api/v1/auth/register",
            json={
                "name": "New Merchant",
                "email": "newmerchant@example.com",
                "password": "weak",
                "business_name": "New Shop",
                "phone_number": "+919998887770",
            },
        )
        assert resp.status_code == 401
        assert "at least 8 characters" in resp.json()["error"]["message"]

        # Test Successful 1-Step Registration
        resp = await ac.post(
            "/api/v1/auth/register",
            json={
                "name": "New Merchant",
                "email": "newmerchant@example.com",
                "password": "StrongPassword123!",
                "business_name": "New Shop",
                "phone_number": "+919998887770",
                "location": "T. Nagar, Chennai",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["role"] == "owner"

        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Verify profile has full shop details set up
        profile_resp = await ac.get("/api/v1/auth/profile", headers=headers)
        assert profile_resp.status_code == 200
        prof = profile_resp.json()
        assert prof["business_name"] == "New Shop"
        assert prof["phone_number"] == "+919998887770"
        assert prof["location"] == "T. Nagar, Chennai"


@pytest.mark.asyncio
async def test_google_auth_flow(test_engine, monkeypatch):
    # Mock firebase token verification
    async def mock_verify_firebase_token(id_token):
        if id_token == "valid_token":
            return {
                "uid": "google-uid-123",
                "email": "googleuser@example.com",
                "name": "Google User",
                "email_verified": True,
            }
        return None

    monkeypatch.setattr("app.core.firebase.verify_firebase_token", mock_verify_firebase_token)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test Invalid Token
        resp = await ac.post("/api/v1/auth/google", json={"id_token": "invalid"})
        assert resp.status_code == 401
        assert "Invalid or expired Google" in resp.json()["error"]["message"]

        # Test Valid Token — Sign Up (New User)
        resp = await ac.post("/api/v1/auth/google", json={"id_token": "valid_token"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["role"] == "owner"
        assert data["needs_onboarding"] is True
        token = data["access_token"]

        # Check that user can onboarding
        headers = {"Authorization": f"Bearer {token}"}
        onboarding_resp = await ac.post(
            "/api/v1/auth/onboarding",
            headers=headers,
            json={
                "business_name": "Google Shop",
                "phone_number": "+919998887777",
                "location": "Velachery, Chennai",
            }
        )
        assert onboarding_resp.status_code == 200

        # Login again (Existing User)
        resp2 = await ac.post("/api/v1/auth/google", json={"id_token": "valid_token"})
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["needs_onboarding"] is False

        # Guard Test: Check that email/password login is rejected for Google-only users
        resp3 = await ac.post(
            "/api/v1/auth/login",
            json={"email": "googleuser@example.com", "password": "AnyPassword123!"}
        )
        assert resp3.status_code == 401
        assert "uses Google Sign-In" in resp3.json()["error"]["message"]


