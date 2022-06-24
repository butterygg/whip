import dateutil.parser
import pandas as pd
import pytest
from dateutil.tz import UTC

from backend.app.spread.actions import update_balances_with_spread
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


def test_token_to_0_percent_usdc():
    balances = Balances(
        balances={"GVT": _make_balance_series([123, 246], ["2022-01-01", "2022-01-02"])}
    )
    spread_balances = update_balances_with_spread(
        balances, "GVT", "USDC", 0, "2022-01-01", "2022-01-02"
    )
    assert "GVT" in spread_balances.balances
    assert "USDC" in spread_balances.balances
    assert (spread_balances.balances["GVT"] + spread_balances.balances["USDC"]).loc[
        "2022-01-01"
    ] == 123
    assert spread_balances.balances["USDC"].tolist() == [0, 0]


def test_token_to_20_percent_usdc():
    balances = Balances(
        balances={"GVT": _make_balance_series([123, 246], ["2022-01-01", "2022-01-02"])}
    )
    spread_balances = update_balances_with_spread(
        balances, "GVT", "USDC", 20, "2022-01-01", "2022-01-02"
    )
    assert "GVT" in spread_balances.balances
    assert "USDC" in spread_balances.balances
    assert (
        spread_balances.balances["GVT"].loc["2022-01-01"]
        + spread_balances.balances["USDC"].loc["2022-01-01"]
        == 123
    )
    assert spread_balances.balances["USDC"].loc["2022-01-01"] == pytest.approx(
        123 * 20 / 100.0
    )


def test_token_to_usdc_earlier_start():
    "Test correct behavior when start date is before any first balance value"
    balances = Balances(
        balances={"GVT": _make_balance_series([123, 246], ["2022-01-02", "2022-01-03"])}
    )
    spread_balances = update_balances_with_spread(
        balances, "GVT", "USDC", 20, "2022-01-01", "2022-01-03"
    )
    assert "GVT" in spread_balances.balances
    assert "USDC" in spread_balances.balances
    assert spread_balances.balances["USDC"].loc["2022-01-01"] == 0


def test_token_to_existing_usdc():
    balances = Balances(
        balances={
            "GVT": _make_balance_series([123, 246], ["2022-01-01", "2022-01-02"]),
            "USDC": _make_balance_series([10, 10], ["2022-01-01", "2022-01-02"]),
        }
    )
    spread_balances = update_balances_with_spread(
        balances, "GVT", "USDC", 20, "2022-01-01", "2022-01-02"
    )
    assert "GVT" in spread_balances.balances
    assert "USDC" in spread_balances.balances
    assert (
        spread_balances.balances["GVT"].loc["2022-01-01"]
        + spread_balances.balances["USDC"].loc["2022-01-01"]
        == 133
    )
    assert spread_balances.balances["USDC"].loc["2022-01-01"] == pytest.approx(
        10 + 123 * 20 / 100.0
    )


def test_token_to_exising_usdc_different_dates():
    "When existing USDC balance series begins later than start date"
    balances = Balances(
        balances={
            "GVT": _make_balance_series(
                [123, 246, 123, 246],
                [
                    "2022-01-01",
                    "2022-01-02",
                    "2022-01-03",
                    "2022-01-04",
                ],
            ),
            "USDC": _make_balance_series(
                [10, 10],
                [
                    "2022-01-03",
                    "2022-01-04",
                ],
            ),
        }
    )
    spread_balances = update_balances_with_spread(
        balances, "GVT", "USDC", 20, "2022-01-01", "2022-01-04"
    )
    assert "GVT" in spread_balances.balances
    assert "USDC" in spread_balances.balances
    assert (
        spread_balances.balances["GVT"].loc["2022-01-01"]
        + spread_balances.balances["USDC"].loc["2022-01-01"]
        == 123
    )
    assert spread_balances.balances["USDC"].loc["2022-01-01"] == pytest.approx(
        123 * 20 / 100.0
    )
