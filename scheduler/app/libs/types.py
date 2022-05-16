from dataclasses import dataclass
from datetime import datetime
from typing import Any, List

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
class PortfolioHistoricalValue(HistoricalPrice):
    treasury_address: str

@dataclass
class Treasury:
    address: str
    assets: List[ERC20]
    historical_prices: List[HistoricalPrice]
    portfolio_value_ts: List[PortfolioHistoricalValue]