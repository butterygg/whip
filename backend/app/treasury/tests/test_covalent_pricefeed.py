# pylint: disable=protected-access
from json import loads

from dateutil.parser import parse
from dateutil.tz import UTC
from fakeredis import FakeRedis
from pytest import MonkeyPatch, mark

from backend.app.treasury.adapters import covalent_pricefeed

from .conftest import covalent_hist_prices_v2_transfers, mocked_datetime


class FakeCovalentResponse:
    resp_json = {"data": covalent_hist_prices_v2_transfers}

    status_code = None

    def raise_for_status(self):
        return None

    def json(self):
        return self.resp_json


async def _get_fake_covalent_resp(*_, **__):
    return FakeCovalentResponse()


@mark.asyncio
async def test_get_coin_hist_price_redis(monkeypatch: MonkeyPatch):
    fake_provider = FakeRedis()
    monkeypatch.setattr(
        "backend.app.treasury.adapters.covalent_pricefeed.db",
        fake_provider,
        raising=True,
    )

    monkeypatch.setattr(
        "backend.app.treasury.adapters.covalent_pricefeed.AsyncClient.get",
        _get_fake_covalent_resp,
        raising=True,
    )

    fake_cache_key_template = "{symbol}_{start}_{end}"
    symbol = "FakeUSDC"
    fake_cache_key = fake_cache_key_template.format(
        symbol=symbol,
        start=mocked_datetime(-366, use_today=True).strftime("%Y-%m-%d"),
        end=mocked_datetime(use_today=True).strftime("%Y-%m-%d"),
    )

    await covalent_pricefeed.get_token_hist_price_covalent("", symbol)

    assert (
        loads(fake_provider.hget("covalent_prices", fake_cache_key))
        == covalent_hist_prices_v2_transfers[0]["prices"]
    )
    assert fake_provider.ttl("covalent_prices") in range(0, 86401)


@mark.asyncio
async def test_get_coin_hist_price(monkeypatch: MonkeyPatch):
    fake_provider = FakeRedis()
    monkeypatch.setattr(
        "backend.app.treasury.adapters.covalent_pricefeed.db",
        fake_provider,
        raising=True,
    )

    monkeypatch.setattr(
        "backend.app.treasury.adapters.covalent_pricefeed.AsyncClient.get",
        _get_fake_covalent_resp,
        raising=True,
    )

    sanitized_prices = await covalent_pricefeed.get_token_hist_price_covalent(
        "", "FakeUSDC"
    )

    assert sanitized_prices == [
        covalent_pricefeed.Price(
            timestamp=parse(item["date"]).replace(tzinfo=UTC),
            value=item["price"],
        )
        for item in covalent_hist_prices_v2_transfers[0]["prices"]
    ]
