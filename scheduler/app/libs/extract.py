from pandas import DataFrame, Series, to_datetime

from .covalent import get_treasury_portfolio, get_treasury, get_token_transfers_for_wallet
from .types import Treasury
from .tasks.get_assets import (
    get_hist_prices_for_portfolio, populate_hist_tres_balance, clean_hist_prices
)
from .pd_inter_calc import portfolio_filler


async def make_treasury(treasury_address: str, chain_id: int) -> Treasury:
    return await get_treasury(await get_treasury_portfolio(treasury_address, chain_id))


def filter_out_small_assets(treasury: Treasury):
    treasury.assets = [
        asset for asset in treasury.assets
        if asset.balance/treasury.usd_total >= 0.5/100
    ]
    return treasury

async def get_sparse_asset_hist_balances(treasury: Treasury) -> dict[str, Series]:
    asset_contract_addresses = {
        asset.token_symbol: asset.token_address for asset in treasury.assets
    }
    transfer_histories = {
        symbol: await get_token_transfers_for_wallet(treasury.address, asset_contract_address)
        for symbol, asset_contract_address in asset_contract_addresses.items()
    }
    maybe_sparse_asset_hist_balances = {
        symbol: await populate_hist_tres_balance(transfer_history)
        for symbol, transfer_history in transfer_histories.items()
    }
    return {
        symbol: hist
        for symbol, hist in maybe_sparse_asset_hist_balances.items()
        if hist is not None and not hist.empty
    }


async def get_token_hist_prices(treasury: Treasury) -> dict[str, DataFrame]:
    maybe_hist_prices = {
        asset.token_symbol: await get_hist_prices_for_portfolio(asset.token_symbol)
        for asset in treasury.assets
    }
    return {symbol: hist for symbol, hist in maybe_hist_prices.items() if hist is not None}

async def augment_token_hist_prices(
    token_hist_prices: dict[str, DataFrame]
) -> dict[str, DataFrame]:
    return {
        symbol: await clean_hist_prices(token_hist_price)
        for symbol, token_hist_price in token_hist_prices.items()
    }

async def fill_asset_hist_balances(
    sparse_asset_hist_balances: dict[str, Series],
    augmented_token_hist_prices: dict[str, DataFrame]
) -> dict[str, DataFrame]:
    def fill_asset_hist_balance(symbol, augmented_token_hist_price):
        if (
            symbol not in sparse_asset_hist_balances or
            len(sparse_asset_hist_balances[symbol]) < 2
        ):
            return None
        quote_rates = Series(data=augmented_token_hist_price["price"])
        quote_rates.index = to_datetime(augmented_token_hist_price["timestamp"])
        return portfolio_filler(sparse_asset_hist_balances[symbol], quote_rates)

    maybe_asset_hist_balance = {
        symbol: fill_asset_hist_balance(symbol, augmented_token_hist_price)
        for symbol, augmented_token_hist_price in augmented_token_hist_prices.items()
    }
    return {
        symbol: asset_hist_balance
        for symbol, asset_hist_balance in maybe_asset_hist_balance.items()
        if asset_hist_balance is not None
    }


async def main(treasury_address: str, chain_id: int) -> tuple[Treasury, dict[str, DataFrame]]:
    treasury = filter_out_small_assets(await make_treasury(treasury_address, chain_id))
    return treasury, await fill_asset_hist_balances(
        await get_sparse_asset_hist_balances(treasury),
        await augment_token_hist_prices(await get_token_hist_prices(treasury))
    )