from functools import reduce
from typing import Optional

import pandas as pd

from .. import db
from ..libs import pd_inter_calc, price_stats
from ..libs import series as serieslib
from ..libs.storage_helpers import maybe_populate_whitelist
from .adapters import bitquery
from .adapters.covalent import get_token_transfers, get_treasury
from .adapters.covalent_pricefeed import get_token_hist_price_covalent
from .models import Balances, BalancesAtTransfers, Prices, TotalBalance, Treasury


async def make_transfers_balances_for_treasury(
    treasury: Treasury,
    token_symbols_and_addresses: set[tuple[str, str]],
    add_eth=True,
) -> BalancesAtTransfers:
    "Returns series of balances defined at times of assets transfers"
    tokens: set[tuple[str, str]] = token_symbols_and_addresses | (
        {("ETH", "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")} if add_eth else set()
    )
    transfers = {
        token_symbol: (
            await bitquery.get_eth_transfers(treasury.address)
            if token_symbol == "ETH"
            else await get_token_transfers(treasury.address, token_address)
        )
        for token_symbol, token_address in tokens
    }
    return BalancesAtTransfers.from_transfer_and_end_balance_dict(
        {
            symbol: (transfers, treasury.get_asset(symbol).balance)
            for symbol, transfers in transfers.items()
        }
    )


async def make_treasury_from_address(treasury_address: str, chain_id: str) -> Treasury:
    token_whitelist = await maybe_populate_whitelist(db)
    return await get_treasury(treasury_address, token_whitelist, chain_id)


async def make_prices_from_tokens(
    token_symbols_and_addresses: set[tuple[str, str]], add_eth=True
) -> Prices:
    """Returns a Prices object only for successful tokens

    Successful tokens are the ones for which the data provider has returned a
    successful result.
    """
    tokens: set[tuple[str, str]] = token_symbols_and_addresses | (
        {("ETH", "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")} if add_eth else {}
    )
    maybe_token_hist_prices = {
        token_symbol: await get_token_hist_price_covalent(token_address, token_symbol)
        for token_symbol, token_address in tokens
    }
    token_prices_series = {
        token_symbol: serieslib.make_hist_price_series(token_symbol, prices)
        for token_symbol, prices in maybe_token_hist_prices.items()
        if prices
    }
    return Prices(
        prices={
            symbol: price_stats.make_returns_df(token_hist_price, "price")
            for symbol, token_hist_price in token_prices_series.items()
        }
    )


async def make_balances_from_treasury_and_prices(
    treasury: Treasury,
    token_symbols_and_addresses: set[tuple[str, str]],
    prices: Prices,
) -> Balances:
    transfers = await make_transfers_balances_for_treasury(
        treasury, token_symbols_and_addresses
    )

    def fill_asset_hist_balance(
        symbol: str, price_series: pd.Series
    ) -> Optional[pd.DataFrame]:
        if symbol not in transfers.balances:
            return None
        return pd_inter_calc.make_daily_hist_balance(
            symbol, transfers.balances[symbol], price_series
        )

    maybe_asset_hist_balance = {
        symbol: fill_asset_hist_balance(symbol, price_df.price)
        for symbol, price_df in prices.prices.items()
    }

    return Balances(
        balances={
            symbol: asset_hist_balance
            for symbol, asset_hist_balance in maybe_asset_hist_balance.items()
            if asset_hist_balance is not None
        }
    )


def update_treasury_assets_from_whitelist(
    treasury: Treasury, token_symbol_whitelist: set[str]
) -> Treasury:
    treasury.assets = [
        a for a in treasury.assets if a.token_symbol in token_symbol_whitelist
    ]
    return treasury


def make_total_balance_from_balances(balances: Balances) -> TotalBalance:
    hist_total_balance: pd.Series = reduce(
        lambda acc, item: acc.add(item, fill_value=0),
        balances.balances.values(),
    )
    return TotalBalance(
        balance=price_stats.make_returns_df(hist_total_balance, "balance")
    )


def update_treasury_assets_risk_contributions(
    treasury: Treasury,
    prices: Prices,
    start: str,
    end: str,
) -> Treasury:
    returns_and_balances = {
        asset.token_symbol: (prices.prices[asset.token_symbol], asset.balance_usd)
        for asset in treasury.assets
    }
    for symbol, risk_contribution in price_stats.calculate_risk_contributions(
        returns_and_balances, start, end
    ).items():
        treasury.get_asset(symbol).risk_contribution = risk_contribution
    return treasury


async def build_treasury_with_assets(
    treasury_address: str, chain_id: int, start: str, end: str
) -> tuple[Treasury, Prices, Balances, TotalBalance]:
    treasury = await make_treasury_from_address(treasury_address, chain_id)

    token_symbols_and_addresses: set[tuple[str, str]] = {
        (asset.token_symbol, asset.token_address) for asset in treasury.assets
    }

    prices = await make_prices_from_tokens(token_symbols_and_addresses)

    balances = await make_balances_from_treasury_and_prices(
        treasury, token_symbols_and_addresses, prices
    )

    treasury = update_treasury_assets_from_whitelist(
        treasury,
        prices.get_existing_token_symbols() | balances.get_existing_token_symbols(),
    )

    total_balance = make_total_balance_from_balances(balances)

    treasury = update_treasury_assets_risk_contributions(
        treasury,
        prices,
        start,
        end,
    )

    return (
        treasury,
        prices,
        balances,
        total_balance,
    )
