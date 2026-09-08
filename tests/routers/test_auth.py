async def _register_user(client, username="user", password="password123"):
    return await client.post("/users/register", json={"username": username, "password": password})


async def _login(client, username="user", password="password123"):
    return await client.post("/auth/login", data={"username": username, "password": password})


# POST /auth/login


async def test_login_success(client):
    await _register_user(client)

    response = await _login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_invalid_credentials(client):
    await _register_user(client)

    response = await _login(client, password="wrong-password")

    assert response.status_code == 401


async def test_login_missing_form_fields(client):
    response = await client.post("/auth/login", data={})

    assert response.status_code == 422


# POST /auth/refresh


async def test_refresh_rotates_token(client):
    await _register_user(client)
    tokens = (await _login(client)).json()

    response = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    assert response.json()["refresh_token"] != tokens["refresh_token"]


async def test_refresh_revoked_token_is_unauthorized(client):
    await _register_user(client)
    tokens = (await _login(client)).json()
    await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    response = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 401


# POST /auth/logout


async def test_logout_revokes_token(client):
    await _register_user(client)
    tokens = (await _login(client)).json()

    response = await client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 204

    refresh_response = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == 401
