from dataclasses import dataclass
from functools import reduce

from ..treasury import ERC20, Treasury


@dataclass
class MultiTreasury:
    addresses: set[str]
    assets: dict[str, ERC20]

    def get_asset(self, symbol: str):
        return next(asset for asset in self.assets if asset.token_symbol == symbol)

    @property
    def usd_total(self) -> float:
        return sum(asset.balance for asset in self.assets)

    @classmethod
    def from_treasuries(cls, treasuries: list[Treasury]) -> "MultiTreasury":
        addresses = {t.address for t in treasuries}
        flattened_assets = ((a.token_symbol, a) for t in treasuries for a in t.assets)

        def reducer(
            assets_accumulator: dict[str, ERC20], symbol_and_asset: tuple[str, ERC20]
        ) -> dict[str, ERC20]:
            token_symbol, asset = symbol_and_asset
            try:
                existing_asset = assets_accumulator.pop(token_symbol)
            except KeyError:
                return {**assets_accumulator, token_symbol: asset}
            else:
                merged_asset = ERC20(
                    token_name=existing_asset.token_name,
                    token_symbol=existing_asset.token_symbol,
                    token_address=existing_asset.token_address,
                    balance=existing_asset.balance + asset.balance,
                )
                return {**assets_accumulator, token_symbol: merged_asset}

        assets = reduce(reducer, flattened_assets, dict())
        return cls(addresses=addresses, assets=assets)
