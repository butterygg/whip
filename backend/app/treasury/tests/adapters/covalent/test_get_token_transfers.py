# pylint: disable=protected-access
# pylint: disable=unused-argument
# pylint: disable=redefined-outer-name

from json import loads

import pytest
from dateutil.parser import parse
from fakeredis import FakeRedis
from httpx import AsyncClient

from ....adapters.covalent import transfers_v2
from .conftest import (
    MockResponse,
    covalent_transfers_v2_transfers,
    mocked_datetime,
    return_mocked_resp,
)


@pytest.fixture
def patch_resp(monkeypatch):
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


@pytest.fixture
def patch_db(monkeypatch):
    fake_provider = FakeRedis()
    monkeypatch.setattr(
        "backend.app.treasury.adapters.covalent.transfers_v2.db", fake_provider
    )


@pytest.mark.asyncio
async def test_successful_output(patch_resp, patch_db):
    sanitized_token_transfers = await transfers_v2.get_token_transfers("0xa", "0xb", 1)
    exp_sanitized_token_transfers = [
        transfers_v2.CovalentTransfer(
            timestamp=parse(
                covalent_transfers_v2_transfers[1]["transfers"][0]["block_signed_at"]
            ),
            balance=int(covalent_transfers_v2_transfers[1]["transfers"][0]["delta"])
            / 1e18,
        ),
        transfers_v2.CovalentTransfer(
            timestamp=parse(
                covalent_transfers_v2_transfers[0]["transfers"][0]["block_signed_at"]
            ),
            balance=int(covalent_transfers_v2_transfers[0]["transfers"][0]["delta"])
            / 1e18
            + int(covalent_transfers_v2_transfers[1]["transfers"][0]["delta"]) / 1e18,
        ),
    ]

    assert sanitized_token_transfers == exp_sanitized_token_transfers


@pytest.mark.asyncio
async def test_successful_cache(patch_resp, patch_db):
    await transfers_v2.get_token_transfers("0xa", "0xb", 1)
    fake_cache_key = "{treasury_address}_{contract_address}_{chain_id}_{date}"

    assert (
        loads(
            transfers_v2.db.hget(
                "covalent_transfers",
                fake_cache_key.format(
                    treasury_address="0xa",
                    contract_address="0xb",
                    chain_id=1,
                    date=mocked_datetime(use_today=True).strftime("%Y-%m-%d"),
                ),
            )
        )
        == MockResponse().json()["data"]  # pylint: disable=unsubscriptable-object
    )
