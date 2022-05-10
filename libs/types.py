from dataclasses import dataclass
from typing import List

@dataclass
class ERC20:
    token_name: str
    token_symbol: str
    token_address: str
    balance: float

@dataclass
class Treasury:
    address: str
    assets: List[ERC20]