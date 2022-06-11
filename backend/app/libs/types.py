import datetime
from dataclasses import dataclass, field


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
    usd_total: float = field(init=False)

    def __post_init__(self):
        self.usd_total = sum(
            asset.balance for asset in self.assets if asset.balance is not None
        )

    def prune(self, symbol: str):
        i = 0
        for asset in self.assets:
            if asset.token_symbol == symbol:
                self.assets.pop(i)
                break
            i += 1

    def get_asset(self, symbol: str):
        return next(asset for asset in self.assets if asset.token_symbol == symbol)


@dataclass
class Transfer:
    timestamp: datetime.datetime
    balance: float  # balance in usd after the transfer


@dataclass
class Price:
    timestamp: datetime.datetime
    value: float
