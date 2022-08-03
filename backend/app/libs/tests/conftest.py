# pylint: disable=unused-argument
# pylint: disable=redefined-outer-name
import asyncio

import pytest
import pytest_asyncio
from _pytest import monkeypatch
from fakeredis import FakeRedis

from ...treasury import actions
from ...treasury.adapters import covalent_pricefeed
from ...treasury.models import Transfer
from .. import pd_inter_calc

covalent_hist_prices_v2_transfers = [
    {
        "contract_decimals": 18,
        "contract_name": "ABC Token",
        "contract_ticker_symbol": "ABC",
        "contract_address": "0x1a5f9352af8af974bfc03399e3767df6370d82e4",
        "supports_erc": ["erc20"],
        "logo_url": "",
        "update_at": "2022-07-13T22:51:12.022553016Z",
        "quote_currency": "USD",
        "prices": [
            {
                "contract_metadata": {
                    "contract_decimals": 18,
                    "contract_name": "ABC Token",
                    "contract_ticker_symbol": "ABC",
                    "contract_address": "0x1a5f9352af8af974bfc03399e3767df6370d82e4",
                    "supports_erc": ["erc20"],
                    "logo_url": "",
                },
                "date": "2022-07-13",
                "price": 0.28732044,
            },
            {
                "contract_metadata": {
                    "contract_decimals": 18,
                    "contract_name": "ABC Token",
                    "contract_ticker_symbol": "ABC",
                    "contract_address": "0x1a5f9352af8af974bfc03399e3767df6370d82e4",
                    "supports_erc": ["erc20"],
                    "logo_url": "",
                },
                "date": "2022-07-12",
                "price": 0.28529906,
            },
            {
                "contract_metadata": {
                    "contract_decimals": 18,
                    "contract_name": "ABC Token",
                    "contract_ticker_symbol": "ABC",
                    "contract_address": "0x1a5f9352af8af974bfc03399e3767df6370d82e4",
                    "supports_erc": ["erc20"],
                    "logo_url": "",
                },
                "date": "2022-07-11",
                "price": 0.28879964,
            },
            {
                "contract_metadata": {
                    "contract_decimals": 18,
                    "contract_name": "ABC Token",
                    "contract_ticker_symbol": "ABC",
                    "contract_address": "0x1a5f9352af8af974bfc03399e3767df6370d82e4",
                    "supports_erc": ["erc20"],
                    "logo_url": "",
                },
                "date": "2022-07-10",
                "price": 0.29183155,
            },
            {
                "contract_metadata": {
                    "contract_decimals": 18,
                    "contract_name": "ABC Token",
                    "contract_ticker_symbol": "ABC",
                    "contract_address": "0x1a5f9352af8af974bfc03399e3767df6370d82e4",
                    "supports_erc": ["erc20"],
                    "logo_url": "",
                },
                "date": "2022-07-09",
                "price": 0.29352316,
            },
        ],
    }
]


class FakeCovalentResponse:
    resp_json = {"data": covalent_hist_prices_v2_transfers}

    status_code = None

    def raise_for_status(self):
        return None

    def json(self):
        return self.resp_json


@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()


@pytest.fixture(scope="module")
def monkeymodule(request):
    _monkeypatch = monkeypatch.MonkeyPatch()
    yield _monkeypatch
    _monkeypatch.undo()


@pytest_asyncio.fixture(scope="module")
async def patch_covalent_pricefeed(monkeymodule):
    async def _get_fake_covalent_resp(*_, **__):
        return FakeCovalentResponse()

    fake_provider = FakeRedis()
    monkeymodule.setattr(
        covalent_pricefeed,
        "db",
        fake_provider,
        raising=True,
    )

    monkeymodule.setattr(
        covalent_pricefeed.AsyncClient,
        "get",
        _get_fake_covalent_resp,
        raising=True,
    )


@pytest.fixture(scope="module")
def patch_today(monkeymodule):
    monkeymodule.setattr(
        pd_inter_calc,
        "today",
        lambda _: pd_inter_calc.datetime.datetime(
            2022, 7, 12, 0, 0, 0, tzinfo=pd_inter_calc.UTC
        ),
    )


@pytest_asyncio.fixture(scope="module")
async def patch_get_token_transfers(monkeymodule):
    async def _implem(*_):
        return [
            Transfer(
                timestamp=pd_inter_calc.datetime.datetime(
                    year=2022,
                    month=7,
                    day=12,
                    hour=22,
                    minute=59,
                    tzinfo=pd_inter_calc.UTC,
                ),
                amount=1,
            ),
        ]

    monkeymodule.setattr(actions, "get_token_transfers", _implem)


@pytest_asyncio.fixture(scope="module")
async def setup_single_transfer_test(
    patch_covalent_pricefeed, patch_today, patch_get_token_transfers
):
    pass
