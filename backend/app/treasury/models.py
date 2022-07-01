import datetime
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ERC20:
    token_name: str
    token_symbol: str
    token_address: str
    balance: float
    risk_contribution: float = field(init=False, repr=False)


@dataclass
class Quote:
    timestamp: datetime.datetime
    quote_rate: float


@dataclass
class HistoricalPrice:
    token_address: str
    token_name: str
    token_symbol: str
    quotes: list[Quote]


@dataclass
class Treasury:
    address: str
    assets: list[ERC20]
    historical_prices: list[HistoricalPrice]

    def get_asset(self, symbol: str):
        return next(asset for asset in self.assets if asset.token_symbol == symbol)

    @property
    def usd_total(self) -> float:
        return sum(asset.balance for asset in self.assets)


@dataclass
class Prices:
    prices: dict[str, pd.DataFrame]

    def get_existing_token_symbols(self) -> set[str]:
        return {*self.prices.keys()}


@dataclass
class Balances:
    balances: dict[str, pd.Series]

    def get_existing_token_symbols(self) -> set[str]:
        return {*self.balances.keys()}


@dataclass
class TotalBalance:
    balance: pd.DataFrame
