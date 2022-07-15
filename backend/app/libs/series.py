import pandas as pd

from .types import Price, Transfer


def make_hist_transfer_series(
    token_symbol: str, transfers: list[Transfer]
) -> pd.Series:
    return pd.Series(
        (transfer.balance for transfer in transfers),
        index=pd.Index(
            (transfer.timestamp for transfer in transfers), name="timestamp"
        ),
        name=f"{token_symbol} historical balance at transfers",
        dtype="float64",
    )


def make_hist_price_series(
    token_symbol: str,
    prices: list[Price],
) -> pd.Series:
    return pd.Series(
        (price.value for price in prices),
        index=pd.Index((price.timestamp for price in prices), name="timestamp"),
        name=f"{token_symbol} historical price",
    )
