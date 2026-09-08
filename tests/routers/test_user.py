def _register_payload(username="user", password="password123"):
    return {"username": username, "password": password}


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
