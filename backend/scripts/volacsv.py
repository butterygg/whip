# pylint: disable=wrong-import-position
# pylint: disable=import-error

import asyncio
import datetime
import sys
from functools import reduce

import dateutil
import dotenv
from clize import run
from pytz import UTC

dotenv.load_dotenv()

from app.treasury import build_treasury_with_assets


def get_volatility(
    address: str,
    start: str = "",
    end: str = "",
):
    today = dateutil.utils.today(UTC)
    end = end or (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    start = start or (today - datetime.timedelta(days=366)).strftime("%Y-%m-%d")
    assert start < end

    treasury, prices, __, ___ = asyncio.run(
        build_treasury_with_assets(address, 1, start, end)
    )

    asset_symbols = [asset.token_symbol for asset in treasury.assets]

    vola_df = reduce(
        lambda acc, df: acc.merge(df, on="timestamp", how="outer"),
        [
            prices.prices[symb][["price"]].rename(columns={"price": symb})
            for symb in asset_symbols
        ],
    )
    vola_df.reset_index(inplace=True)
    vola_df["date"] = vola_df.timestamp.dt.date
    vola_df.set_index("date", inplace=True)
    del vola_df["timestamp"]

    sys.stdout.write(vola_df.to_csv())


if __name__ == "__main__":
    run(get_volatility)
