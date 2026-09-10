def _register_payload(username="user", password="password123"):
    return {"username": username, "password": password}


async def _register_user(client, username="user", password="password123"):
    return await client.post(
        "/users/register", json=_register_payload(username=username, password=password)
    )


async def test_register_user_success(client):
    response = await client.post("/users/register", json=_register_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["username"] == "user"
    assert "password" not in body["user"]
    assert body["access_token"]


async def test_register_user_duplicate_conflict(client):
    await client.post("/users/register", json=_register_payload())

    response = await client.post("/users/register", json=_register_payload())

    assert response.status_code == 409


async def test_register_user_invalid_payload(client):
    response = await client.post(
        "/users/register", json=_register_payload(username="ab", password="short")
    )

    assert response.status_code == 422


# GET /users/me


async def test_get_me_returns_authenticated_user(client):
    registration = await _register_user(client, username="current-user")
    access_token = registration.json()["access_token"]

    response = await client.get("/users/me", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    assert response.json() == {
        "id": registration.json()["user"]["id"],
        "username": "current-user",
    }


async def test_get_me_without_access_token_is_unauthorized(client):
    response = await client.get("/users/me")

    assert response.status_code == 401


async def test_get_me_with_invalid_access_token_is_unauthorized(client):
    response = await client.get("/users/me", headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401
