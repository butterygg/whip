import pandas as pd

from ..treasury import (
    ERC20,
    Balances,
    Prices,
    TotalBalance,
    Treasury,
    make_balances_from_transfers_and_prices,
    make_prices_from_tokens,
    make_total_balance_from_balances,
    make_transfers_balances_for_treasury,
    make_treasury_from_address,
    update_treasury_assets_from_whitelist,
    update_treasury_assets_risk_contributions,
)
from .models import SpreadTokenSymbol


def update_balances_with_spread(
    balances: Balances,
    token_to_divest_from: str,
    spread_token_symbol: SpreadTokenSymbol,
    spread_percentage: int,
    hist_spread_price: pd.Series,
    start: str,
    end: str,
) -> Balances:
    resized_balances = balances.copy()

    if token_to_divest_from == spread_token_symbol:
        return resized_balances

    divest_token_hist_balances = balances.usd_balances[token_to_divest_from]

    try:
        divest_token_start_usd_balance = divest_token_hist_balances.loc[start]
    except KeyError:
        divest_token_start_usd_balance = 0

    # Do not resize divest token balance if no swap was possible.
    if divest_token_start_usd_balance > 0:
        resized_balances.usd_balances[token_to_divest_from] *= (
            100 - spread_percentage
        ) / 100.0

    # USD balance to add to spread token at start of period:
    spread_token_new_usd_balance_at_start = (
        divest_token_start_usd_balance * spread_percentage / 100
    )
    # Token balance at start (divide by quote on that day):
    spread_token_new_balance_at_start = (
        spread_token_new_usd_balance_at_start / hist_spread_price.loc[start]
    )
    # USD balance to add to spread token (scale balance-of-1 USD series by
    # the balance-at-start scalar):
    # Note on "balance-of-1": the USD balance series for a portfolio
    # holding a spread token balance of exactly 1 is the same as historical
    # price series.
    spread_token_new_usd_balance = (
        hist_spread_price.loc[start:end] * spread_token_new_balance_at_start
    )

    # Define new spread token balance by adding the new USD balance on top of
    # the existing one.
    resized_balances.usd_balances[spread_token_symbol] = (
        spread_token_new_usd_balance.add(
            resized_balances.usd_balances[spread_token_symbol], fill_value=0
        )
        if spread_token_symbol in resized_balances.usd_balances
        else spread_token_new_usd_balance
    )

    return resized_balances


def update_treasury_assets_with_spread_balances(
    treasury: Treasury,
    balances: Balances,
    end: str,
    spread_token_name: str,
    spread_token_symbol: SpreadTokenSymbol,
    spread_token_address: str,
) -> Treasury:
    for asset in treasury.assets:
        asset.balance_usd = balances.usd_balances[asset.token_symbol].loc[end]
    try:
        treasury.get_asset(spread_token_symbol)
    except StopIteration:
        treasury.assets.append(
            ERC20(
                token_name=spread_token_name,
                token_symbol=spread_token_symbol,
                token_address=spread_token_address,
                balance_usd=balances.usd_balances[spread_token_symbol].loc[end],
                balance=0,  # We don't care about balance now.
            )
        )
    return treasury


def get_usd_quote(
    spread_token_symbol: str, end: str
):  # pylint: disable=unused-argument
    if spread_token_symbol == "USDC":
        return 1.0
    raise NotImplementedError()


async def build_spread_treasury_with_assets(
    treasury_address: str,
    chain_id: int,
    start: str,
    end: str,
    token_to_divest_from: str,
    spread_token_name: str,
    spread_token_symbol: SpreadTokenSymbol,
    spread_token_address: str,
    spread_percentage: int,
) -> tuple[Treasury, Prices, Balances, TotalBalance]:
    treasury = await make_treasury_from_address(treasury_address, chain_id)

    assert token_to_divest_from in (asset.token_symbol for asset in treasury.assets)

    token_symbols_and_addresses_with_spread_token: set[tuple[str, str]] = {
        (asset.token_symbol, asset.token_address) for asset in treasury.assets
    } | {(spread_token_symbol, spread_token_address)}
    prices = await make_prices_from_tokens(
        token_symbols_and_addresses_with_spread_token
    )

    balances_at_transfers = await make_transfers_balances_for_treasury(treasury)

    balances = await make_balances_from_transfers_and_prices(
        balances_at_transfers, prices
    )

    treasury = update_treasury_assets_from_whitelist(
        treasury,
        prices.get_existing_token_symbols() | balances.get_existing_token_symbols(),
    )

    balances = update_balances_with_spread(
        balances,
        token_to_divest_from,
        spread_token_symbol,
        spread_percentage,
        prices.prices[spread_token_symbol]["price"],
        start,
        end,
    )
    treasury = update_treasury_assets_with_spread_balances(
        treasury,
        balances,
        end,
        spread_token_name,
        spread_token_symbol,
        spread_token_address,
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
