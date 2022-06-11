import math

import dateutil.parser
import numpy as np

from backend.app.libs import price_stats
from backend.app.libs import series as serieslib
from backend.app.libs.types import Price


def _make_price_from_strdate(price: float, strdate: str) -> Price:
    return Price(value=price, timestamp=dateutil.parser.parse(strdate))


def test_no_price():
    hist_price = serieslib.make_hist_price_series("TEST", [])

    assert price_stats.make_returns_df(hist_price, "price").empty


def test_one_price():
    hist_price = serieslib.make_hist_price_series(
        "TEST", [_make_price_from_strdate(price=42.42, strdate="2022-02-22")]
    )

    returns_df = price_stats.make_returns_df(hist_price, "price")

    assert len(returns_df) == 1
    assert returns_df.price.loc["2022-02-22"] == 42.42
    assert np.isnan(returns_df.returns.loc["2022-02-22"])
    assert np.isnan(returns_df.std_dev.loc["2022-02-22"])


def test_two_prices():
    hist_price = serieslib.make_hist_price_series(
        "TEST",
        [
            _make_price_from_strdate(price=42.42, strdate="2022-02-22"),
            _make_price_from_strdate(price=43.43, strdate="2022-02-23"),
        ],
    )

    returns_df = price_stats.make_returns_df(hist_price, "price")

    assert len(returns_df) == 2
    assert np.isnan(returns_df.returns.loc["2022-02-22"])
    assert returns_df.returns.loc["2022-02-23"] == math.log(43.43 / 42.42)
    assert np.isnan(returns_df.std_dev).all()


def test_prev_zero():
    hist_price = serieslib.make_hist_price_series(
        "TEST",
        [
            _make_price_from_strdate(price=0, strdate="2022-02-22"),
            _make_price_from_strdate(price=43.43, strdate="2022-02-23"),
        ],
    )

    returns_df = price_stats.make_returns_df(hist_price, "price")

    assert np.isnan(returns_df.returns.loc["2022-02-22"])
    assert returns_df.returns.loc["2022-02-23"] == 0
    assert np.isnan(returns_df.std_dev).all()


def test_current_zero():
    hist_price = serieslib.make_hist_price_series(
        "TEST",
        [
            _make_price_from_strdate(price=42.42, strdate="2022-02-22"),
            _make_price_from_strdate(price=0, strdate="2022-02-23"),
        ],
    )

    returns_df = price_stats.make_returns_df(hist_price, "price")

    assert np.isnan(returns_df.returns.loc["2022-02-22"])
    assert returns_df.returns.loc["2022-02-23"] == 0
    assert np.isnan(returns_df.std_dev).all()


def test_two_zeroes():
    hist_price = serieslib.make_hist_price_series(
        "TEST",
        [
            _make_price_from_strdate(price=0, strdate="2022-02-22"),
            _make_price_from_strdate(price=0, strdate="2022-02-23"),
        ],
    )

    returns_df = price_stats.make_returns_df(hist_price, "price")

    assert np.isnan(returns_df.returns.loc["2022-02-22"])
    assert returns_df.returns.loc["2022-02-23"] == 0
    assert np.isnan(returns_df.std_dev).all()


def test_8_prices():
    hist_price = serieslib.make_hist_price_series(
        "TEST",
        [
            _make_price_from_strdate(price=p, strdate=s)
            for p, s in [
                (2, "2022-01-01"),
                (1, "2022-01-02"),
                (0, "2022-01-03"),
                (2, "2022-01-04"),
                (4, "2022-01-05"),
                (8, "2022-01-06"),
                (16, "2022-01-07"),
                (1, "2022-01-08"),
                (0, "2022-01-09"),
            ]
        ],
    )

    returns_df = price_stats.make_returns_df(hist_price, "price")

    assert returns_df.std_dev.loc["2022-01-08"] > 0
    assert returns_df.std_dev.loc["2022-01-09"] > 0
