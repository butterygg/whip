""" Test for token and treasury data providers
"""

from datetime import datetime
from json import loads
from json.decoder import JSONDecodeError

from httpx import AsyncClient
from pytest import MonkeyPatch, mark, raises

from backend.app.libs.coingecko.coins import _get_data, get_data

from ..conftest import HTTPStatusError, raise_http_status_error_404

# Coingecko Tests


class MockResponse:
    status_code = None
    text = ""

    def raise_for_status(self):
        return None

    @staticmethod
    def json():
        return {
            "prices": [
                [1590019200000, 0.9993188217729783],
                [1590105600000, 0.9981200719764681],
                [1590192000000, 0.9995106820722109],
                [1590278400000, 0.9984064931995519],
                [1590364800000, 0.9941101041414783],
            ]
        }


async def return_mocked_resp(*_, **__):
    return MockResponse()


def mock_datetime(offset: int = 0):
    return datetime(2022, 1, 1 + offset)


@mark.asyncio
async def test_coins_success(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)

    resp = await get_data("", mock_datetime(), mock_datetime(5))

    assert resp == [
        [1590019200000, 0.9993188217729783],
        [1590105600000, 0.9981200719764681],
        [1590192000000, 0.9995106820722109],
        [1590278400000, 0.9984064931995519],
        [1590364800000, 0.9941101041414783],
    ]


@mark.asyncio
async def test_coins_status_err(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(MockResponse, "raise_for_status", raise_http_status_error_404)

    with raises(HTTPStatusError) as error:
        prices = await _get_data("", mock_datetime(), mock_datetime(5))

        assert not prices
        assert "mocked http status error" in error.value


@mark.asyncio
async def test_coins_successful_retry(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr("backend.app.libs.coingecko.coins.sleep", lambda *_: None)
    monkeypatch.setattr(
        MockResponse, "text", "rate limit reached\nplease try again in a minute"
    )

    prices = await get_data("", mock_datetime(), mock_datetime(5))

    assert prices == [
        [1590019200000, 0.9993188217729783],
        [1590105600000, 0.9981200719764681],
        [1590192000000, 0.9995106820722109],
        [1590278400000, 0.9984064931995519],
        [1590364800000, 0.9941101041414783],
    ]


@mark.asyncio
async def test_coins_bad_json_err(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(MockResponse, "json", lambda *_: loads("bad json response"))

    with raises(JSONDecodeError):
        prices = await _get_data("", mock_datetime(), mock_datetime(5))

        assert not prices
