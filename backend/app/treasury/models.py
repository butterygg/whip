import datetime
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Price:
    timestamp: datetime.datetime
    value: float


@dataclass
class Transfer:
    timestamp: datetime.datetime
    amount: float  # amount of tokens transferred


@dataclass
class BalancesAtTransfers:
    balances: dict[str, pd.Series]

    @staticmethod
    def _make_balance_series(
        token_symbol: str,
        transfers: list[Transfer],
        end_balance: float,
    ) -> pd.Series:
        amount_series = pd.Series(
            (transfer.amount for transfer in transfers),
            index=pd.Index(
                (transfer.timestamp for transfer in transfers), name="timestamp"
            ),
            dtype="float64",
        ).sort_index()
        cumulative_amount_series = amount_series.expanding(1).sum()
        balance_series = cumulative_amount_series + (
            end_balance - cumulative_amount_series.iloc[-1]
        )
        balance_series.name = f"{token_symbol} balance at transfer times"
        return balance_series

    @classmethod
    def from_transfer_and_end_balance_dict(
        cls,
        transfers_dict: dict[str, tuple[list[Transfer], float]],
    ) -> "BalancesAtTransfers":
        return cls(
            balances={
                token_symbol: cls._make_balance_series(
                    token_symbol, *transfers_and_end_balance
                )
                for token_symbol, transfers_and_end_balance in transfers_dict.items()
            }
        )


@dataclass
class ERC20:
    token_name: str
    token_symbol: str
    token_address: str
    balance_usd: float
    balance: float
    risk_contribution: float = field(init=False, repr=False)


@dataclass
class Treasury:
    address: str
    assets: list[ERC20]

    def get_asset(self, symbol: str):
        return next(asset for asset in self.assets if asset.token_symbol == symbol)

    @property
    def usd_total(self) -> float:
        return sum(asset.balance_usd for asset in self.assets)


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

    def copy(self):
        return Balances(
            balances={
                token_symbol: balance_series.copy(deep=True)
                for token_symbol, balance_series in self.balances.items()
            }
        )


@dataclass
class TotalBalance:
    balance: pd.DataFrame
