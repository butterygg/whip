import datetime
from dataclasses import dataclass


@dataclass
class Transfer:
    timestamp: datetime.datetime
    balance: float  # balance in usd after the transfer


@dataclass
class Price:
    timestamp: datetime.datetime
    value: float
