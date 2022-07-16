# pylint: disable=protected-access
from json import loads
from json.decoder import JSONDecodeError
from unittest import mock

import pytest
from httpx import AsyncClient

from ....adapters.covalent import transfers_v2
from .conftest import (
    HTTPStatusError,
    MockResponse,
    covalent_transfers_v2_transfers,
    make_mock_response_with_json,
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
                "pagination": {
                    "has_more": False,
                    "page_number": 0,
                    "page_size": 100,
                    "total_count": None,
                },
            },
        },
    )

    treasury_transfers = [
        _
        async for _ in transfers_v2._get_transfer_items(
            "0x6d6f636b65645f7472656173757279", "", 1
        )
    ]

    assert treasury_transfers == covalent_transfers_v2_transfers


@pytest.mark.asyncio
async def test_covalent_transfers_multipage_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        AsyncClient,
        "get",
        mock.AsyncMock(
            side_effect=[
                make_mock_response_with_json(
                    {
                        "data": {
                            "address": "0x6d6f636b65645f7472656173757279",
                            "quote_currency": "USD",
                            "chain_id": 1,
                            "items": covalent_transfers_v2_transfers[0:1],
                            "pagination": {
                                "has_more": True,
                                "page_number": 0,
                                "page_size": 1,
                                "total_count": None,
                            },
                        },
                    }
                ),
                make_mock_response_with_json(
                    {
                        "data": {
                            "address": "0x6d6f636b65645f7472656173757279",
                            "quote_currency": "USD",
                            "chain_id": 1,
                            "items": covalent_transfers_v2_transfers[1:],
                            "pagination": {
                                "has_more": False,
                                "page_number": 1,
                                "page_size": 100,
                                "total_count": None,
                            },
                        },
                    }
                ),
            ]
        ),
    )

    treasury_transfers = [
        _
        async for _ in transfers_v2._get_transfer_items(
            "0x6d6f636b65645f7472656173757279", "", 1
        )
    ]

    assert treasury_transfers == covalent_transfers_v2_transfers


@pytest.mark.asyncio
async def test_covalent_transfers_status_err(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(MockResponse, "raise_for_status", raise_http_status_error_404)

    with pytest.raises(HTTPStatusError) as error:
        async for _ in transfers_v2._get_transfer_items("", "", 1):
            pass

    assert "mocked http status error" in error.value.args


@pytest.mark.asyncio
async def test_covalent_transfers_bad_resp_json(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(MockResponse, "json", lambda *_: {"dtaa": "{...}"})

    with pytest.raises(KeyError):
        async for _ in transfers_v2._get_transfer_items("", "", 1):
            pass


@pytest.mark.asyncio
async def test_covalent_transfers_bad_json_err(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(AsyncClient, "get", return_mocked_resp)
    monkeypatch.setattr(MockResponse, "json", lambda *_: loads("bad json response"))

    with pytest.raises(JSONDecodeError):
        async for _ in transfers_v2._get_transfer_items("", "", 1):
            pass
