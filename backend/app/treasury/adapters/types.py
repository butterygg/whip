import datetime
from dataclasses import dataclass
from typing import Any, TypeVar, Union


@dataclass
class Transfer:
    timestamp: datetime.datetime
    balance: float  # balance in usd after the transfer


@dataclass
class Price:
    timestamp: datetime.datetime
    value: float


RawPrices = TypeVar("RawPrices", list[list[Union[int, float]]], list[Any])
