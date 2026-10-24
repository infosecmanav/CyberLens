from fastapi.testclient import TestClient


def test_register_login_and_current_user(client: TestClient) -> None:
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "analyst@example.com",
            "display_name": "Example Analyst",
            "password": "correct horse battery staple",
        },
    )
    assert registration.status_code == 201
    assert registration.json()["role"] == "ADMIN"

    duplicate = client.post(
        "/api/v1/auth/register",
        json={
            "email": "analyst@example.com",
            "display_name": "Example Analyst",
            "password": "correct horse battery staple",
        },
    )
    assert duplicate.status_code == 409

    login = client.post(
        "/api/v1/auth/token",
        data={"username": "analyst@example.com", "password": "correct horse battery staple"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    current_user = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert current_user.status_code == 200
    assert current_user.json()["email"] == "analyst@example.com"


def test_rejects_invalid_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401
