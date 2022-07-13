# pylint: disable=protected-access

import datetime
from unittest.mock import Mock

import pytest
from pytz import UTC

from ..models import BalancesAtTransfers, Transfer


def test_make_series_from_transfers_without_balances():
    transfers = [
        Transfer(
            timestamp=datetime.datetime(year=2022, month=1, day=1, tzinfo=UTC),
            amount=333,
        ),
        Transfer(
            timestamp=datetime.datetime(year=2022, month=1, day=2, tzinfo=UTC),
            amount=1,
        ),
        Transfer(
            timestamp=datetime.datetime(year=2022, month=1, day=10, tzinfo=UTC),
            amount=10,
        ),
    ]

    series = BalancesAtTransfers._make_balance_series(
        "whatever", transfers, end_balance=1000
    )
    assert [_.date() for _ in series.index.to_list()] == [
        datetime.date(year=2022, month=1, day=1),
        datetime.date(year=2022, month=1, day=2),
        datetime.date(year=2022, month=1, day=10),
    ]
    assert series.to_list() == [989.0, 990.0, 1000.0]


def test_make_series_from_unordered_transfers_without_balances():
    transfers = [
        Transfer(
            timestamp=datetime.datetime(year=2030, month=1, day=1, tzinfo=UTC),
            amount=1,
        ),
        Transfer(
            timestamp=datetime.datetime(year=2030, month=1, day=2, tzinfo=UTC),
            amount=3,
        ),
        Transfer(
            timestamp=datetime.datetime(year=2022, month=1, day=1, tzinfo=UTC),
            amount=1232,
        ),
    ]

    series = BalancesAtTransfers._make_balance_series("whatever", transfers, 1004)
    assert [_.date() for _ in series.index.to_list()] == [
        datetime.date(year=2022, month=1, day=1),
        datetime.date(year=2030, month=1, day=1),
        datetime.date(year=2030, month=1, day=2),
    ]
    assert series.to_list() == [1000.0, 1001.0, 1004.0]


def test_constructor_from_transfers(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        BalancesAtTransfers, "_make_balance_series", Mock(return_value="series_mock")
    )
    mocked_make_balance_series: Mock = BalancesAtTransfers._make_balance_series

    balances_at_transfers = BalancesAtTransfers.from_transfer_and_end_balance_dict(
        {
            "USDC": (["dummy"], 111),
            "ETH": (["dummy2", "dummy3"], 333),
        }
    )

    assert balances_at_transfers == BalancesAtTransfers(
        balances={"ETH": "series_mock", "USDC": "series_mock"}
    )
    mocked_make_balance_series.assert_any_call("ETH", ["dummy2", "dummy3"], 333)
    mocked_make_balance_series.assert_any_call("USDC", ["dummy"], 111)
