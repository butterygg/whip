import dateutil.parser
import pandas as pd
import pytest
from dateutil.tz import UTC

from backend.app.spread.actions import _resize_balances, update_balances_with_spread
from backend.app.spread.helpers import make_zeroes
from backend.app.treasury import Balances


def _make_balance_series(balances: list[float], strdates: list[str]) -> pd.Series:
    return pd.Series(
        balances,
        index=pd.Index(
            [
                dateutil.parser.parse(strdate).replace(tzinfo=UTC)
                for strdate in strdates
            ],
            name="timestamp",
        ),
    )


def test_0_percents():
    assert _resize_balances({"a": 1, "b": 2, "c": 3}, 0) == {
        "a": 1,
        "b": 2,
        "c": 3,
    }


def test_20_percents():
    assert _resize_balances({"a": 1, "b": 2, "c": 3}, 20) == {
        "a": pytest.approx(0.8),
        "b": pytest.approx(1.6),
        "c": pytest.approx(2.4),
    }


def test_set_zeroes():
    zeroes_series = make_zeroes(
        "2021-01-01",
        "2021-01-05",
    )
    assert all(zeroes_series.values == [0, 0, 0, 0, 0])
    assert [str(v)[:10] for v in zeroes_series.index.values] == [
        "2021-01-01",
        "2021-01-02",
        "2021-01-03",
        "2021-01-04",
        "2021-01-05",
    ]


def test_apply_spread_to_balances_no_usdc():
    balances = Balances(
        balances={"DAI": _make_balance_series([123, 246], ["2021-01-01", "2021-01-02"])}
    )
    spreaded_balances = update_balances_with_spread(
        balances, "USDC", 20, "2021-01-01", "2021-01-02"
    )
    assert "DAI" in spreaded_balances.balances
    assert "USDC" in spreaded_balances.balances
    assert (
        spreaded_balances.balances["DAI"].loc["2021-01-01"]
        + spreaded_balances.balances["USDC"].loc["2021-01-01"]
        == 123
    )


def test_apply_spread_to_balances_no_usdc_earlier_start():
    "Test correct behavior when start date is before any first balance value"
    balances = Balances(
        balances={"DAI": _make_balance_series([123, 246], ["2021-01-02", "2021-01-03"])}
    )
    spreaded_balances = update_balances_with_spread(
        balances, "USDC", 20, "2021-01-01", "2021-01-03"
    )
    assert "DAI" in spreaded_balances.balances
    assert "USDC" in spreaded_balances.balances
    assert spreaded_balances.balances["USDC"].loc["2021-01-01"] == 0


def test_apply_spread_to_balances_with_usdc():
    balances = Balances(
        balances={
            "DAI": _make_balance_series([123, 246], ["2021-01-01", "2021-01-02"]),
            "USDC": _make_balance_series([10, 10], ["2021-01-01", "2021-01-02"]),
        }
    )
    spreaded_balances = update_balances_with_spread(
        balances, "USDC", 20, "2021-01-01", "2021-01-02"
    )
    assert "DAI" in spreaded_balances.balances
    assert "USDC" in spreaded_balances.balances
    assert (
        spreaded_balances.balances["DAI"].loc["2021-01-01"]
        + spreaded_balances.balances["USDC"].loc["2021-01-01"]
        == 133
    )


def test_apply_spread_to_balances_with_usdc_different_dates():
    "When existing USDC balance series begins later than start date"
    balances = Balances(
        balances={
            "DAI": _make_balance_series(
                [123, 246, 123, 246],
                [
                    "2021-01-01",
                    "2021-01-02",
                    "2021-01-03",
                    "2021-01-04",
                ],
            ),
            "USDC": _make_balance_series(
                [10, 10],
                [
                    "2021-01-03",
                    "2021-01-04",
                ],
            ),
        }
    )
    spreaded_balances = update_balances_with_spread(
        balances, "USDC", 20, "2021-01-01", "2021-01-04"
    )
    assert "DAI" in spreaded_balances.balances
    assert "USDC" in spreaded_balances.balances
    assert (
        spreaded_balances.balances["DAI"].loc["2021-01-01"]
        + spreaded_balances.balances["USDC"].loc["2021-01-01"]
        == 123
    )
