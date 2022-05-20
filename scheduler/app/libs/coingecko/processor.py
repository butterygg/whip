from datetime import datetime
from dateutil.tz import UTC
from typing import Any, Dict, List

from pandas import DataFrame as DF, MultiIndex, to_datetime

def coingecko_hist_df(contract_address: str, symbol: str, resp: List[List[int]]) -> DF:
    prices = []
    timestamps = []
    for i in range(0, len(resp) - 1):
        day = resp[i]

        prices.append(day[1])
        timestamps.append(
            to_datetime(datetime.fromtimestamp(int(day[0] / 1000), tz=UTC))
        )

    index = MultiIndex.from_tuples(
        [
            (ts, contract_address, symbol) for ts in timestamps
        ],
        names=["timestamp", "address", "symbol"]
    )
    
    return DF(prices, index=index, columns=["price"]).reset_index()
