import asyncio
import time

import httpx
import pytest

from groster.http_client import BlizzardAPIClient, _validate_region

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def token_response():
    return httpx.Response(
        200,
        json={"access_token": "test-token-abc", "expires_in": 3600},
        request=httpx.Request("POST", "https://oauth.battle.net/token"),
    )


@pytest.fixture()
def client(token_response, mocker):
    """Create a BlizzardAPIClient with a pre-seeded token (no real HTTP)."""
    c = BlizzardAPIClient(
        region="eu",
        client_id="id",
        client_secret="secret",
    )
    mocker.patch.object(c.client, "post", return_value=token_response)
    return c


# ---------------------------------------------------------------------------
# _validate_region
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("region", ["us", "eu", "kr", "tw", "cn"])
def test_validate_region_supported_region_does_not_raise(region):
    _validate_region(region)


def test_validate_region_unsupported_region_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported region 'xx'"):
        _validate_region("xx")


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


def test_init_valid_params_creates_client():
    c = BlizzardAPIClient(region="eu", client_id="id", client_secret="secret")

    assert c.region == "eu"
    assert c.client_id == "id"
    assert c.max_retries == 5


def test_init_missing_params_raises_value_error():
    with pytest.raises(ValueError, match="Region, client ID, and client secret"):
        BlizzardAPIClient(region="", client_id="id", client_secret="secret")


def test_init_invalid_region_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported region"):
        BlizzardAPIClient(region="xx", client_id="id", client_secret="secret")


# ---------------------------------------------------------------------------
# _format_url
# ---------------------------------------------------------------------------


def test_format_url_eu_region_uses_region_host():
    c = BlizzardAPIClient(region="eu", client_id="id", client_secret="secret")

    result = c._format_url("/some/path")

    assert result == "https://eu.api.blizzard.com/some/path"


def test_format_url_cn_region_uses_cn_host():
    c = BlizzardAPIClient(region="cn", client_id="id", client_secret="secret")

    result = c._format_url("some/path")

    assert result == "https://gateway.battlenet.com.cn/some/path"


def test_format_url_strips_leading_slash():
    c = BlizzardAPIClient(region="us", client_id="id", client_secret="secret")

    result = c._format_url("///path")

    assert result == "https://us.api.blizzard.com/path"


# ---------------------------------------------------------------------------
# _get_access_token
# ---------------------------------------------------------------------------


def test_get_access_token_fetches_new_token(client):
    token = asyncio.run(client._get_access_token())

    assert token == "test-token-abc"
    assert client._api_token == "test-token-abc"
    assert client._token_expires_at > time.time()


def test_get_access_token_reuses_cached_token(client, mocker):
    client._api_token = "cached-token"
    client._token_expires_at = time.time() + 9999

    token = asyncio.run(client._get_access_token())

    assert token == "cached-token"
    client.client.post.assert_not_called()


def test_get_access_token_refreshes_expired_token(client):
    client._api_token = "old-token"
    client._token_expires_at = time.time() - 1

    token = asyncio.run(client._get_access_token())

    assert token == "test-token-abc"


def test_get_access_token_missing_token_in_response_raises(client):
    client.client.post.return_value = httpx.Response(
        200,
        json={"token_type": "bearer"},
        request=httpx.Request("POST", "https://oauth.battle.net/token"),
    )

    with pytest.raises(ValueError, match="access_token"):
        asyncio.run(client._get_access_token())


def test_get_access_token_http_error_raises(client):
    client.client.post.return_value = httpx.Response(
        401,
        json={"error": "unauthorized"},
        request=httpx.Request("POST", "https://oauth.battle.net/token"),
    )

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(client._get_access_token())


# ---------------------------------------------------------------------------
# _request — success path
# ---------------------------------------------------------------------------


def test_request_success_returns_json(client, mocker):
    mock_resp = httpx.Response(
        200,
        json={"data": "ok"},
        request=httpx.Request("GET", "https://eu.api.blizzard.com/test"),
    )
    mocker.patch.object(client.client, "request", return_value=mock_resp)

    result = asyncio.run(client._request("GET", "https://eu.api.blizzard.com/test"))

    assert result == {"data": "ok"}


# ---------------------------------------------------------------------------
# _request — retry on transient errors
# ---------------------------------------------------------------------------


def test_request_retries_on_429_then_succeeds(client, mocker):
    rate_limited = httpx.Response(
        429,
        headers={"Retry-After": "0"},
        request=httpx.Request("GET", "https://eu.api.blizzard.com/x"),
    )
    success = httpx.Response(
        200,
        json={"ok": True},
        request=httpx.Request("GET", "https://eu.api.blizzard.com/x"),
    )
    mocker.patch.object(client.client, "request", side_effect=[rate_limited, success])
    mocker.patch("groster.http_client.asyncio.sleep", return_value=None)

    result = asyncio.run(client._request("GET", "https://eu.api.blizzard.com/x"))

    assert result == {"ok": True}


@pytest.mark.parametrize("status_code", [500, 502, 503, 504])
def test_request_retries_on_5xx_then_succeeds(client, mocker, status_code):
    error_resp = httpx.Response(
        status_code,
        request=httpx.Request("GET", "https://eu.api.blizzard.com/x"),
    )
    success = httpx.Response(
        200,
        json={"ok": True},
        request=httpx.Request("GET", "https://eu.api.blizzard.com/x"),
    )
    mocker.patch.object(client.client, "request", side_effect=[error_resp, success])
    mocker.patch("groster.http_client.asyncio.sleep", return_value=None)

    result = asyncio.run(client._request("GET", "https://eu.api.blizzard.com/x"))

    assert result == {"ok": True}


def test_request_retry_after_header_integer_used_as_delay(client, mocker):
    rate_limited = httpx.Response(
        429,
        headers={"Retry-After": "7"},
        request=httpx.Request("GET", "https://eu.api.blizzard.com/x"),
    )
    success = httpx.Response(
        200,
        json={"ok": True},
        request=httpx.Request("GET", "https://eu.api.blizzard.com/x"),
    )
    mocker.patch.object(client.client, "request", side_effect=[rate_limited, success])
    sleep_mock = mocker.patch("groster.http_client.asyncio.sleep", return_value=None)

    asyncio.run(client._request("GET", "https://eu.api.blizzard.com/x"))

    sleep_mock.assert_any_call(7)


def test_request_max_retries_exceeded_returns_empty_dict(client, mocker):
    client.max_retries = 2
    error_resp = httpx.Response(
        503,
        request=httpx.Request("GET", "https://eu.api.blizzard.com/x"),
    )
    mocker.patch.object(
        client.client,
        "request",
        return_value=error_resp,
    )
    mocker.patch("groster.http_client.asyncio.sleep", return_value=None)

    result = asyncio.run(client._request("GET", "https://eu.api.blizzard.com/x"))

    assert result == {}


# ---------------------------------------------------------------------------
# _request — error paths
# ---------------------------------------------------------------------------


def test_request_network_error_retries_then_returns_empty(client, mocker):
    client.max_retries = 2
    req = httpx.Request("GET", "https://eu.api.blizzard.com/x")
    mocker.patch.object(
        client.client,
        "request",
        side_effect=httpx.ConnectError("connection refused", request=req),
    )
    mocker.patch("groster.http_client.asyncio.sleep", return_value=None)

    result = asyncio.run(client._request("GET", "https://eu.api.blizzard.com/x"))

    assert result == {}
    assert client.client.request.call_count == 2


def test_request_http_status_error_breaks_immediately(client, mocker):
    client.max_retries = 3
    resp_403 = httpx.Response(
        403,
        text="Forbidden",
        request=httpx.Request("GET", "https://eu.api.blizzard.com/x"),
    )
    mocker.patch.object(
        client.client,
        "request",
        return_value=resp_403,
    )

    result = asyncio.run(client._request("GET", "https://eu.api.blizzard.com/x"))

    assert result == {}
    assert client.client.request.call_count == 1


# ---------------------------------------------------------------------------
# Public API methods
# ---------------------------------------------------------------------------


def test_get_guild_roster_calls_request_with_correct_url(client, mocker):
    mocker.patch.object(client, "_request", return_value={"members": []})

    result = asyncio.run(client.get_guild_roster("terokkar", "darq-side-of-the-moon"))

    assert result == {"members": []}
    call_args = client._request.call_args
    assert "guild/terokkar/darq-side-of-the-moon/roster" in call_args[0][1]


def test_get_character_profile_lowercases_name(client, mocker):
    mocker.patch.object(client, "_request", return_value={"name": "Darq"})

    asyncio.run(client.get_character_profile("terokkar", "Darq"))

    url = client._request.call_args[0][1]
    assert "/character/terokkar/darq" in url


def test_get_character_achievements_builds_correct_path(client, mocker):
    mocker.patch.object(client, "_request", return_value={})

    asyncio.run(client.get_character_achievements("terokkar", "Darq"))

    url = client._request.call_args[0][1]
    assert "/character/terokkar/darq/achievements" in url


def test_get_character_pets_builds_correct_path(client, mocker):
    mocker.patch.object(client, "_request", return_value={})

    asyncio.run(client.get_character_pets("terokkar", "Darq"))

    url = client._request.call_args[0][1]
    assert "/character/terokkar/darq/collections/pets" in url


def test_get_character_mounts_builds_correct_path(client, mocker):
    mocker.patch.object(client, "_request", return_value={})

    asyncio.run(client.get_character_mounts("terokkar", "Darq"))

    url = client._request.call_args[0][1]
    assert "/character/terokkar/darq/collections/mounts" in url


def test_get_playable_classes_returns_classes_list(client, mocker):
    mocker.patch.object(
        client,
        "_request",
        return_value={"classes": [{"id": 1, "name": "Warrior"}]},
    )

    result = asyncio.run(client.get_playable_classes())

    assert result == [{"id": 1, "name": "Warrior"}]


def test_get_playable_races_returns_races_list(client, mocker):
    mocker.patch.object(
        client,
        "_request",
        return_value={"races": [{"id": 1, "name": "Human"}]},
    )

    result = asyncio.run(client.get_playable_races())

    assert result == [{"id": 1, "name": "Human"}]


def test_get_playable_classes_empty_response_returns_empty_list(client, mocker):
    mocker.patch.object(client, "_request", return_value={})

    result = asyncio.run(client.get_playable_classes())

    assert result == []


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


def test_context_manager_enter_returns_self():
    async def _run():
        async with BlizzardAPIClient(
            region="eu", client_id="id", client_secret="secret"
        ) as c:
            return c

    c = asyncio.run(_run())

    assert isinstance(c, BlizzardAPIClient)


def test_context_manager_exit_closes_session(mocker):
    async def _run():
        c = BlizzardAPIClient(region="eu", client_id="id", client_secret="secret")
        close_mock = mocker.patch.object(c, "close", return_value=None)
        async with c:
            pass
        return close_mock

    close_mock = asyncio.run(_run())

    close_mock.assert_called_once()
