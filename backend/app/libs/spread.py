from typing import Union

import pandas as pd
from pytz import UTC

Balance = Union[float, pd.Series]


def resize_balances(
    balances: dict[str, Balance],
    spread_percentage: int,
) -> dict[str, Balance]:
    downsizing_factor = (100 - spread_percentage) / 100.0

    return {k: b * downsizing_factor for k, b in balances.items()}


def make_zeroes(start: str, end: str) -> pd.Series:
    return pd.Series(0, index=pd.date_range(start, end, tz=UTC))


def apply_spread_to_balances(
    balances: dict[str, pd.Series],
    spread_token_symbol: str,
    spread_percentage: int,
    start: str,
    end: str,
) -> dict[str, pd.Series]:
    def get_default_balance(histbal: pd.DataFrame) -> float:
        try:
            return histbal.loc[start]
        except KeyError:
            return 0

    initial_total_balance = sum(map(get_default_balance, balances.values()))
    resized_balances = resize_balances(balances, spread_percentage)
    zeroes_series = make_zeroes(start, end)
    spread_additional_token_balance = zeroes_series + (
        initial_total_balance * spread_percentage / 100.0
    )
    spread_additional_token_balance.name = (
        f"{spread_token_symbol} spread backtest balance"
    )
    if spread_token_symbol in resized_balances:
        spread_additional_token_balance = spread_additional_token_balance.add(
            resized_balances[spread_token_symbol], fill_value=0
        )
    resized_balances[spread_token_symbol] = spread_additional_token_balance
    return resized_balances
