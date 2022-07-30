# pylint: disable=unused-argument
# pylint: disable=redefined-outer-name

import datetime
from unittest.mock import Mock

import pytest
import pytest_asyncio
from pytz import UTC

from .. import actions
from ..models import ERC20, Transfer, Treasury


@pytest_asyncio.fixture
async def patch_get_token_transfers(monkeypatch: pytest.MonkeyPatch):
    async def _implem(*_):
        return [
            Transfer(
                timestamp=datetime.datetime(year=2030, month=1, day=1, tzinfo=UTC),
                amount=1232,
            ),
            Transfer(
                timestamp=datetime.datetime(year=2022, month=1, day=1, tzinfo=UTC),
                amount=1,
            ),
        ]

    monkeypatch.setattr(actions, "get_token_transfers", _implem)


@pytest.fixture
def patch_balances_at_transfers_constructor(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        actions.BalancesAtTransfers,
        "from_transfer_and_end_balance_dict",
        Mock(return_value="balances_at_transfers_mock"),
    )
    mocked_constructor: Mock = (
        actions.BalancesAtTransfers.from_transfer_and_end_balance_dict
    )
    return mocked_constructor


@pytest.mark.asyncio
async def test_make_transfers_for_treasury(
    patch_get_token_transfers, patch_balances_at_transfers_constructor
):

    treasury = Treasury(
        address="0x0",
        assets=[
            ERC20(
                token_name="abc",
                token_symbol="ABC",
                token_address="0xabc",
                balance=1000,
                balance_usd=2,
            ),
            ERC20(
                token_name="def",
                token_symbol="DEF",
                token_address="0xdef",
                balance=333,
                balance_usd=3,
            ),
        ],
    )

    balances_at_transfers = await actions.make_transfers_balances_for_treasury(treasury)

    assert balances_at_transfers == "balances_at_transfers_mock"
    assert patch_balances_at_transfers_constructor.call_args[0][0] == (
        {
            "ABC": (
                [
                    Transfer(
                        timestamp=datetime.datetime(2030, 1, 1, 0, 0, tzinfo=UTC),
                        amount=1232,
                    ),
                    Transfer(
                        timestamp=datetime.datetime(2022, 1, 1, 0, 0, tzinfo=UTC),
                        amount=1,
                    ),
                ],
                1000,
            ),
            "DEF": (
                [
                    Transfer(
                        timestamp=datetime.datetime(2030, 1, 1, 0, 0, tzinfo=UTC),
                        amount=1232,
                    ),
                    Transfer(
                        timestamp=datetime.datetime(2022, 1, 1, 0, 0, tzinfo=UTC),
                        amount=1,
                    ),
                ],
                333,
            ),
        }
    )
