from dataclasses import dataclass, field
from datetime import datetime
from typing import List

@dataclass
class ERC20:
    token_name: str
    token_symbol: str
    token_address: str
    balance: float

@dataclass
class Quote:
    ts: datetime
    quote_rate: float

@dataclass
class HistoricalPrice:
    token_address: str
    token_name: str
    token_symbol: str
    quotes: List[Quote]

@dataclass
class Treasury:
    address: str
    assets: List[ERC20]
    historical_prices: List[HistoricalPrice]
    usd_total: float = field(init=False)

    def __post_init__(self):
        self.usd_total = sum(
            asset.balance for asset in self.assets
            if asset.balance is not None
        )