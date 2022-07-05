# pylint: disable=protected-access
from copy import deepcopy
from datetime import datetime, timedelta
from json import loads
from json.decoder import JSONDecodeError

from dateutil.parser import parse
from dateutil.tz import UTC
from dateutil.utils import today as today_in
from fakeredis import FakeRedis
from httpx import AsyncClient
from pytest import MonkeyPatch, mark, raises

from backend.app.treasury.adapters import covalent

from .conftest import (
    HTTPStatusError,
    covalent_portfolio_v2_transfers,
    covalent_transfers_v2_transfers,
    raise_http_status_error_404,
    spam_token_transfer,
)


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
async def test_covalent_transfers_success(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(
        MockResponse,
        "json",
        lambda *_: {
            "data": {
                "address": "0x6d6f636b65645f7472656173757279",
                "quote_currency": "USD",
                "chain_id": 1,
                "items": covalent_transfers_v2_transfers,
            }
        },
    )

    treasury_transfers = await covalent.get_transfer_data(
        "0x6d6f636b65645f7472656173757279", "", 1
    )

    assert treasury_transfers == {
        "address": "0x6d6f636b65645f7472656173757279",
        "quote_currency": "USD",
        "chain_id": 1,
        "items": covalent_transfers_v2_transfers,
    }


@mark.asyncio
async def test_covalent_transfers_status_err(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(MockResponse, "raise_for_status", raise_http_status_error_404)

    with raises(HTTPStatusError) as error:
        treasury_transfers = await covalent._get_transfer_data("", "", 1)

        assert not treasury_transfers
        assert "mocked http status error" in error.value


@mark.asyncio
async def test_covalent_transfers_bad_resp_json(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(MockResponse, "json", lambda *_: {"dtaa": "{...}"})

    with raises(KeyError):
        treasury_transfers = await covalent._get_transfer_data("", "", 1)

        assert not treasury_transfers


@mark.asyncio
async def test_covalent_transfers_bad_json_err(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(MockResponse, "json", lambda *_: loads("bad json response"))

    with raises(JSONDecodeError):
        treasury_transfers = await covalent._get_transfer_data("", "", 1)

        assert not treasury_transfers


@mark.asyncio
async def test_covalent_transfers_bad_transfers(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    _covalent_transfers_v2_transfers = deepcopy(covalent_transfers_v2_transfers)
    for item in _covalent_transfers_v2_transfers:
        del item["transfers"]

    with raises(KeyError):
        tokens = list(
            covalent._gen_transfers(
                {
                    "address": "0x6d6f636b65645f7472656173757279",
                    "quote_currency": "USD",
                    "chain_id": 1,
                    "items": _covalent_transfers_v2_transfers,
                }
            )
        )

        assert not tokens

    _covalent_transfers_v2_transfers = deepcopy(covalent_transfers_v2_transfers)
    for item in _covalent_transfers_v2_transfers:
        del item["transfers"][0]["contract_decimals"]

    with raises(KeyError):
        tokens = list(
            covalent._gen_transfers(
                {
                    "address": "0x6d6f636b65645f7472656173757279",
                    "quote_currency": "USD",
                    "chain_id": 1,
                    "items": _covalent_transfers_v2_transfers,
                }
            )
        )

        assert not tokens


@mark.asyncio
async def test_covalent_get_token_transfers(monkeypatch: MonkeyPatch):
    fake_provider = FakeRedis()
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr("backend.app.treasury.adapters.covalent.db", fake_provider)
    monkeypatch.setattr(
        MockResponse,
        "json",
        lambda *_: {
            "data": {
                "address": "0x6d6f636b65645f7472656173757279",
                "quote_currency": "USD",
                "chain_id": 1,
                "items": covalent_transfers_v2_transfers,
            }
        },
    )

    sanitized_token_transfers = await covalent.get_token_transfers("0xa", "0xb", 1)
    exp_sanitized_token_transfers = [
        covalent.CovalentTransfer(
            timestamp=parse(
                covalent_transfers_v2_transfers[1]["transfers"][0]["block_signed_at"]
            ),
            balance=int(covalent_transfers_v2_transfers[1]["transfers"][0]["delta"])
            / 1e18,
        ),
        covalent.CovalentTransfer(
            timestamp=parse(
                covalent_transfers_v2_transfers[0]["transfers"][0]["block_signed_at"]
            ),
            balance=int(covalent_transfers_v2_transfers[0]["transfers"][0]["delta"])
            / 1e18
            + int(covalent_transfers_v2_transfers[1]["transfers"][0]["delta"]) / 1e18,
        ),
    ]

    assert sanitized_token_transfers == exp_sanitized_token_transfers

    fake_cache_key = "{treasury_address}_{contract_address}_{chain_id}_{date}"
    assert (
        loads(
            fake_provider.hget(
                "covalent_transfers",
                fake_cache_key.format(
                    treasury_address="0xa",
                    contract_address="0xb",
                    chain_id=1,
                    date=mocked_datetime(use_today=True).strftime("%Y-%m-%d"),
                ),
            )
        )
        == MockResponse().json()["data"]
    )


@mark.asyncio
async def test_get_treasury_portfolio_success(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(
        MockResponse,
        "json",
        lambda *_: {
            "data": {
                "address": "0x6d6f636b65645f7472656173757279",
                "quote_currency": "USD",
                "chain_id": 1,
                "items": covalent_portfolio_v2_transfers,
            }
        },
    )

    portfolio_hist_balances = await covalent._get_treasury_portfolio("", 1)

    assert portfolio_hist_balances == {
        "address": "0x6d6f636b65645f7472656173757279",
        "quote_currency": "USD",
        "chain_id": 1,
        "items": covalent_portfolio_v2_transfers,
    }


@mark.asyncio
async def test_get_treasury_portfolio_status_err(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(MockResponse, "raise_for_status", raise_http_status_error_404)

    with raises(HTTPStatusError) as error:
        portfolio_hist_balances = await covalent._get_treasury_portfolio("", 1)

        assert not portfolio_hist_balances
        assert "mocked http status error" in error.value


@mark.asyncio
async def test_get_treasury_portfolio_bad_resp_json(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(
        MockResponse,
        "json",
        lambda *_: {"dtaa": "{...}"},
    )

    with raises(KeyError):
        portfolio_hist_balances = await covalent._get_treasury_portfolio("", 1)

        assert not portfolio_hist_balances


@mark.asyncio
async def test_get_treasury_portfolio_bad_json_err(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(
        MockResponse,
        "json",
        lambda *_: loads("bad json response"),
    )

    with raises(JSONDecodeError):
        portfolio_hist_balances = await covalent._get_treasury_portfolio("", 1)

        assert not portfolio_hist_balances


@mark.asyncio
async def test_get_treasury_success(monkeypatch: MonkeyPatch):
    fake_provider = FakeRedis()
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr("backend.app.treasury.adapters.covalent.db", fake_provider)

    covalent_portfolio_v2_transfers.append(spam_token_transfer)
    monkeypatch.setattr(
        MockResponse,
        "json",
        lambda *_: {
            "data": {
                "address": "0x6d6f636b65645f7472656173757279",
                "quote_currency": "USD",
                "chain_id": 1,
                "items": covalent_portfolio_v2_transfers,
            }
        },
    )

    treasury = await covalent.get_treasury(
        await covalent.get_treasury_portfolio("", 1),
        ["0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"],
    )

    asset = covalent.ERC20(
        token_name=covalent_portfolio_v2_transfers[0]["contract_name"],
        token_symbol=covalent_portfolio_v2_transfers[0]["contract_ticker_symbol"],
        token_address=covalent_portfolio_v2_transfers[0]["contract_address"],
        balance=covalent_portfolio_v2_transfers[0]["holdings"][0]["close"]["quote"],
    )
    asset.risk_contribution = None
    treasury.assets[0].risk_contribution = None
    assert treasury == covalent.Treasury(
        address="0x6d6f636b65645f7472656173757279",
        assets=[asset],
        historical_prices=[
            covalent.HistoricalPrice(
                covalent_portfolio_v2_transfers[0]["contract_address"],
                covalent_portfolio_v2_transfers[0]["contract_name"],
                covalent_portfolio_v2_transfers[0]["contract_ticker_symbol"],
                [
                    covalent.Quote(parse(holding["timestamp"]), holding["quote_rate"])
                    for holding in covalent_portfolio_v2_transfers[0]["holdings"]
                ],
            )
        ],
    )
