# pylint: disable=pointless-statement

import dateutil.parser
import pandas as pd
import pytest
from dateutil.tz import UTC

from ...treasury import Balances
from ..actions import update_balances_with_spread


def _make_series(balances: list[float], strdates: list[str]) -> pd.Series:
    return pd.Series(
        balances,
        index=pd.Index(
            [
                dateutil.parser.parse(strdate).replace(tzinfo=UTC)
                for strdate in strdates
            ],
            name="timestamp",
        ),
        dtype="float64",
    )


def test_0_percent():
    balances = Balances(
        usd_balances={"GVT": _make_series([123, 246], ["2022-01-01", "2022-01-02"])}
    )
    hist_price = _make_series([3000, 2000], ["2022-01-01", "2022-01-02"])

    spread_balances = update_balances_with_spread(
        balances, "GVT", "ETH", 0, hist_price, "2022-01-01", "2022-01-02"
    )

    assert "GVT" in spread_balances.usd_balances
    assert "ETH" in spread_balances.usd_balances
    # Check invariant: total balance on start date.
    assert (
        spread_balances.usd_balances["GVT"] + spread_balances.usd_balances["ETH"]
    ).loc["2022-01-01"] == 123
    assert spread_balances.usd_balances["ETH"].tolist() == [0, 0]
    assert spread_balances.usd_balances["GVT"].tolist() == [123, 246]


def test_20_percent():
    balances = Balances(
        usd_balances={"GVT": _make_series([200, 400], ["2022-01-01", "2022-01-02"])}
    )
    hist_price = _make_series([3000, 2000], ["2022-01-01", "2022-01-02"])

    spread_balances = update_balances_with_spread(
        balances, "GVT", "ETH", 20, hist_price, "2022-01-01", "2022-01-02"
    )

    # Check invariant: total balance on start date.
    assert (
        spread_balances.usd_balances["GVT"].loc["2022-01-01"]
        + spread_balances.usd_balances["ETH"].loc["2022-01-01"]
        == 200
    )
    # Check balances
    assert spread_balances.usd_balances["GVT"].tolist() == pytest.approx([160.0, 320.0])
    assert spread_balances.usd_balances["ETH"].tolist() == pytest.approx(
        [40.0, 40.0 * 2000 / 3000]
    )


def test_earlier_start():
    "When start date is before any first balance value, no backtest swap happens"
    balances = Balances(
        usd_balances={"GVT": _make_series([123, 246], ["2022-01-02", "2022-01-03"])}
    )
    hist_price = _make_series([1, 1, 1], ["2022-01-01", "2022-01-02", "2022-01-03"])

    spread_balances = update_balances_with_spread(
        balances, "GVT", "USDC", 20, hist_price, "2022-01-01", "2022-01-03"
    )

    assert spread_balances.usd_balances["USDC"].loc["2022-01-01"] == 0
    assert spread_balances.usd_balances["USDC"].tolist() == [0, 0, 0]
    pd.testing.assert_series_equal(
        spread_balances.usd_balances["GVT"], balances.usd_balances["GVT"]
    )


def test_existing_spread_token_balance():
    balances = Balances(
        usd_balances={
            "GVT": _make_series([200, 400], ["2022-01-01", "2022-01-02"]),
            "ETH": _make_series([10, 0], ["2022-01-01", "2022-01-02"]),
        }
    )
    hist_price = _make_series([3000, 2000], ["2022-01-01", "2022-01-02"])

    spread_balances = update_balances_with_spread(
        balances, "GVT", "ETH", 20, hist_price, "2022-01-01", "2022-01-02"
    )

    # Check invariant: total balance on start date.
    assert (
        spread_balances.usd_balances["GVT"].loc["2022-01-01"]
        + spread_balances.usd_balances["ETH"].loc["2022-01-01"]
        == 210
    )
    # Check balances.
    assert spread_balances.usd_balances["GVT"].tolist() == pytest.approx([160, 320])
    assert spread_balances.usd_balances["ETH"].tolist() == pytest.approx(
        [10 + 40, 40 * 2000 / 3000]
    )


def test_existing_spread_token_late():
    "When existing spread token balance series begins later than start date"
    balances = Balances(
        usd_balances={
            "GVT": _make_series(
                [200, 400, 800, 1600],
                [
                    "2022-01-01",
                    "2022-01-02",
                    "2022-01-03",
                    "2022-01-04",
                ],
            ),
            "ETH": _make_series(
                [10, 5],
                [
                    "2022-01-03",
                    "2022-01-04",
                ],
            ),
        }
    )
    hist_price = _make_series(
        [3000, 2000, 2500, 1500],
        ["2022-01-01", "2022-01-02", "2022-01-03", "2022-01-04"],
    )

    spread_balances = update_balances_with_spread(
        balances, "GVT", "ETH", 20, hist_price, "2022-01-01", "2022-01-04"
    )

    # Check invariant: total balance on start date.
    assert (
        spread_balances.usd_balances["GVT"].loc["2022-01-01"]
        + spread_balances.usd_balances["ETH"].loc["2022-01-01"]
        == 200
    )
    # Check balances.
    assert spread_balances.usd_balances["GVT"].tolist() == pytest.approx(
        [160, 320, 640, 1280]
    )
    assert spread_balances.usd_balances["ETH"].tolist() == pytest.approx(
        [40, 40 * 2000 / 3000, 10 + 40 * 2500 / 3000, 5 + 40 * 1500 / 3000]
    )
