# pylint: disable=protected-access
from json import loads
from json.decoder import JSONDecodeError

import pytest
from httpx import AsyncClient

from ....adapters.covalent import portfolio_v2
from .conftest import (
    HTTPStatusError,
    MockResponse,
    covalent_portfolio_v2_transfers,
    raise_http_status_error_404,
    return_mocked_resp,
)


@pytest.mark.asyncio
async def test_get_treasury_portfolio_success(monkeypatch):
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

    portfolio_hist_balances = await portfolio_v2._get_portfolio_data("", 1)

    assert portfolio_hist_balances == {
        "address": "0x6d6f636b65645f7472656173757279",
        "quote_currency": "USD",
        "chain_id": 1,
        "items": covalent_portfolio_v2_transfers,
    }


@pytest.mark.asyncio
async def test_get_treasury_portfolio_status_err(monkeypatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(MockResponse, "raise_for_status", raise_http_status_error_404)

    with pytest.raises(HTTPStatusError) as error:
        await portfolio_v2._get_portfolio_data("", 1)

    assert "mocked http status error" in error.value.args


@pytest.mark.asyncio
async def test_get_treasury_portfolio_bad_resp_json(monkeypatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(
        MockResponse,
        "json",
        lambda *_: {"dtaa": "{...}"},
    )

    with pytest.raises(KeyError):
        await portfolio_v2._get_portfolio_data("", 1)


@pytest.mark.asyncio
async def test_get_treasury_portfolio_bad_json_err(monkeypatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(
        MockResponse,
        "json",
        lambda *_: loads("bad json response"),
    )

    with pytest.raises(JSONDecodeError):
        await portfolio_v2._get_portfolio_data("", 1)
