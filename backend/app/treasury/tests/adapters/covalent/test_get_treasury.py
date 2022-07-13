# pylint: disable=protected-access
# pylint: disable=unused-argument
# pylint: disable=redefined-outer-name
import pytest
from fakeredis import FakeRedis
from httpx import AsyncClient

from ....adapters.covalent import portfolio_v2
from ....models import ERC20, Treasury
from .conftest import (
    MockResponse,
    covalent_portfolio_v2_transfers,
    return_mocked_resp,
    spam_token_transfer,
)


@pytest.fixture
def patch_resp(monkeypatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
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


@pytest.fixture
def patch_db(monkeypatch):
    fake_provider = FakeRedis()
    monkeypatch.setattr(
        "backend.app.treasury.adapters.covalent.portfolio_v2.db", fake_provider
    )


@pytest.mark.asyncio
async def test_get_treasury_success(patch_resp, patch_db):
    treasury = await portfolio_v2.get_treasury(
        "", ["0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"], 1
    )

    asset = ERC20(
        token_name=covalent_portfolio_v2_transfers[0]["contract_name"],
        token_symbol=covalent_portfolio_v2_transfers[0]["contract_ticker_symbol"],
        token_address=covalent_portfolio_v2_transfers[0]["contract_address"],
        balance_usd=covalent_portfolio_v2_transfers[0]["holdings"][0]["close"]["quote"],
        balance=int(
            covalent_portfolio_v2_transfers[0]["holdings"][0]["close"]["balance"]
        )
        / 10 ** int(covalent_portfolio_v2_transfers[0]["contract_decimals"]),
    )
    asset.risk_contribution = None
    treasury.assets[0].risk_contribution = None
    assert treasury == Treasury(
        address="0x6d6f636b65645f7472656173757279",
        assets=[asset],
    )
