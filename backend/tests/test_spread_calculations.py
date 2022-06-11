import dateutil.parser
import pandas as pd
import pytest
from dateutil.tz import UTC

from backend.app.libs.spread import (
    apply_spread_to_balances,
    make_zeroes,
    resize_balances,
)


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
    assert resize_balances({"a": 1, "b": 2, "c": 3}, 0) == {
        "a": 1,
        "b": 2,
        "c": 3,
    }


def test_20_percents():
    assert resize_balances({"a": 1, "b": 2, "c": 3}, 20) == {
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
    balances = {"DAI": _make_balance_series([123, 246], ["2021-01-01", "2021-01-02"])}
    spreaded_balances = apply_spread_to_balances(
        balances, "USDC", 20, "2021-01-01", "2021-01-02"
    )
    assert "DAI" in spreaded_balances
    assert "USDC" in spreaded_balances
    assert (
        spreaded_balances["DAI"].loc["2021-01-01"]
        + spreaded_balances["USDC"].loc["2021-01-01"]
        == 123
    )


def test_apply_spread_to_balances_no_usdc_earlier_start():
    "Test correct behavior when start date is before any first balance value"
    balances = {"DAI": _make_balance_series([123, 246], ["2021-01-02", "2021-01-03"])}
    spreaded_balances = apply_spread_to_balances(
        balances, "USDC", 20, "2021-01-01", "2021-01-03"
    )
    assert "DAI" in spreaded_balances
    assert "USDC" in spreaded_balances
    assert spreaded_balances["USDC"].loc["2021-01-01"] == 0


def test_apply_spread_to_balances_with_usdc():
    balances = {
        "DAI": _make_balance_series([123, 246], ["2021-01-01", "2021-01-02"]),
        "USDC": _make_balance_series([10, 10], ["2021-01-01", "2021-01-02"]),
    }
    spreaded_balances = apply_spread_to_balances(
        balances, "USDC", 20, "2021-01-01", "2021-01-02"
    )
    assert "DAI" in spreaded_balances
    assert "USDC" in spreaded_balances
    assert (
        spreaded_balances["DAI"].loc["2021-01-01"]
        + spreaded_balances["USDC"].loc["2021-01-01"]
        == 133
    )


def test_apply_spread_to_balances_with_usdc_different_dates():
    "When existing USDC balance series begins later than start date"
    balances = {
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
    spreaded_balances = apply_spread_to_balances(
        balances, "USDC", 20, "2021-01-01", "2021-01-04"
    )
    assert "DAI" in spreaded_balances
    assert "USDC" in spreaded_balances
    assert (
        spreaded_balances["DAI"].loc["2021-01-01"]
        + spreaded_balances["USDC"].loc["2021-01-01"]
        == 123
    )
