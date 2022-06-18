from datetime import datetime

from dateutil.tz import UTC
from pandas import DataFrame as DF
from pandas import MultiIndex, to_datetime


def coingecko_hist_df(contract_address: str, symbol: str, resp: list[list[int]]) -> DF:
    """Return a DataFrame representation of a Coingecko token price timeseries.

    Parameters
    ---
    contract_address: str
        The token's ERC20 contract address
    symbol: str
        The token's ERC20 symbol
    resp: List[List[int]]
        Response from `libs.coingecko.coins.get_coin_hist_price`;
        A list of [timestamp, quote_rate] pairs
    """
    prices = []
    timestamps = []
    for i in range(0, len(resp) - 1):
        day = resp[i]

        prices.append(day[1])
        timestamps.append(
            to_datetime(datetime.fromtimestamp(int(day[0] / 1000), tz=UTC))
        )

    index = MultiIndex.from_tuples(
        [(ts, contract_address, symbol) for ts in timestamps],
        names=["timestamp", "address", "symbol"],
    )

    return DF(prices, index=index, columns=["price"]).reset_index()
