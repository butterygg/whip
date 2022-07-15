# pylint: disable=protected-access
from copy import deepcopy
from json import loads
from json.decoder import JSONDecodeError

import pytest
from httpx import AsyncClient

from ....adapters.covalent import transfers_v2
from .conftest import (
    HTTPStatusError,
    MockResponse,
    covalent_transfers_v2_transfers,
    raise_http_status_error_404,
    return_mocked_resp,
)


@pytest.mark.asyncio
async def test_covalent_transfers_success(monkeypatch: pytest.MonkeyPatch):
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

    treasury_transfers = await transfers_v2._get_transfers_data(
        "0x6d6f636b65645f7472656173757279", "", 1
    )

    assert treasury_transfers == {
        "address": "0x6d6f636b65645f7472656173757279",
        "quote_currency": "USD",
        "chain_id": 1,
        "items": covalent_transfers_v2_transfers,
    }


@pytest.mark.asyncio
async def test_covalent_transfers_status_err(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(MockResponse, "raise_for_status", raise_http_status_error_404)

    with pytest.raises(HTTPStatusError) as error:
        await transfers_v2._get_transfers_data("", "", 1)

    assert "mocked http status error" in error.value.args


@pytest.mark.asyncio
async def test_covalent_transfers_bad_resp_json(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(MockResponse, "json", lambda *_: {"dtaa": "{...}"})

    with pytest.raises(KeyError):
        await transfers_v2._get_transfers_data("", "", 1)


@pytest.mark.asyncio
async def test_covalent_transfers_bad_json_err(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(MockResponse, "json", lambda *_: loads("bad json response"))

    with pytest.raises(JSONDecodeError):
        await transfers_v2._get_transfers_data("", "", 1)


@pytest.mark.asyncio
async def test_missing_transfers(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    _covalent_transfers_v2_transfers = deepcopy(covalent_transfers_v2_transfers)
    for item in _covalent_transfers_v2_transfers:
        del item["transfers"]

    with pytest.raises(KeyError):
        list(
            transfers_v2._gen_transfers(
                {
                    "address": "0x6d6f636b65645f7472656173757279",
                    "quote_currency": "USD",
                    "chain_id": 1,
                    "items": _covalent_transfers_v2_transfers,
                }
            )
        )


@pytest.mark.asyncio
async def test_bad_transfers_decimals(monkeypatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)

    _covalent_transfers_v2_transfers = deepcopy(covalent_transfers_v2_transfers)
    for item in _covalent_transfers_v2_transfers:
        del item["transfers"][0]["contract_decimals"]

    with pytest.raises(KeyError):
        list(
            transfers_v2._gen_transfers(
                {
                    "address": "0x6d6f636b65645f7472656173757279",
                    "quote_currency": "USD",
                    "chain_id": 1,
                    "items": _covalent_transfers_v2_transfers,
                }
            )
        )
