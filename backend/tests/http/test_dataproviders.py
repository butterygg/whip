# pylint: disable=protected-access
""" Test for token and treasury data providers' adapters
"""

from datetime import datetime, timedelta
from json import loads
from json.decoder import JSONDecodeError

from dateutil.tz import UTC
from dateutil.utils import today as today_in
from fakeredis import FakeRedis
from httpx import AsyncClient
from pytest import MonkeyPatch, mark, raises

from backend.app.libs.coingecko import coins
from backend.app.libs.types import Price

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


def mocked_datetime(offset: int = 0, use_today: bool = False):
    _mocked_datetime = datetime(2022, 1, 1) if not use_today else today_in(UTC)
    return _mocked_datetime + timedelta(offset)


@mark.asyncio
async def test_coins_success(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)

    resp = await coins.get_data("", mocked_datetime(), mocked_datetime(5))

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
        prices = await coins._get_data("", mocked_datetime(), mocked_datetime(5))

        assert not prices
        assert "mocked http status error" in error.value


@mark.asyncio
async def test_coins_successful_retry(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr("backend.app.libs.coingecko.coins.sleep", lambda *_: None)
    monkeypatch.setattr(
        MockResponse, "text", "rate limit reached\nplease try again in a minute"
    )

    prices = await coins.get_data("", mocked_datetime(), mocked_datetime(5))

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
        prices = await coins._get_data("", mocked_datetime(), mocked_datetime(5))

        assert not prices


@mark.asyncio
async def test_coins_get_coin_hist_price(monkeypatch: MonkeyPatch):
    fake_provider = FakeRedis()
    monkeypatch.setattr("backend.app.libs.coingecko.coins.db", fake_provider)
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)

    fake_cache_key_template = "{symbol}_{start}_{end}"
    symbol = "FakeUSDC"
    fake_cache_key = fake_cache_key_template.format(
        symbol=symbol,
        start=mocked_datetime(-366, use_today=True).strftime("%Y-%m-%d"),
        end=mocked_datetime(use_today=True).strftime("%Y-%m-%d"),
    )

    sanitized_prices = await coins.get_coin_hist_price("", symbol)
    assert loads(fake_provider.hget("coingecko_hist_prices", fake_cache_key)) == [
        [1590019200000, 0.9993188217729783],
        [1590105600000, 0.9981200719764681],
        [1590192000000, 0.9995106820722109],
        [1590278400000, 0.9984064931995519],
        [1590364800000, 0.9941101041414783],
    ]
    assert fake_provider.ttl("coingecko_hist_prices") in range(0, 86401)
    assert sanitized_prices == [
        Price(
            timestamp=datetime.fromtimestamp(int(epoch_time / 1000), tz=UTC),
            value=price,
        )
        for epoch_time, price in [
            [1590019200000, 0.9993188217729783],
            [1590105600000, 0.9981200719764681],
            [1590192000000, 0.9995106820722109],
            [1590278400000, 0.9984064931995519],
            [1590364800000, 0.9941101041414783],
        ]
    ]
