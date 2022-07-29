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
from .helpers import make_zeroes


def update_balances_with_spread(
    balances: Balances,
    token_to_divest_from: str,
    spread_token_symbol: str,
    spread_percentage: int,
    start: str,
    end: str,
) -> Balances:
    resized_balances = balances.copy()

    if token_to_divest_from == spread_token_symbol:
        return resized_balances

    zeroes_series = make_zeroes(start, end)

    try:
        start_divest_balance = balances.balances[token_to_divest_from].loc[start]
    except KeyError:
        spread_additional_token_balance: pd.Series = zeroes_series
    else:
        spread_additional_token_balance: pd.Series = (
            zeroes_series + start_divest_balance * spread_percentage / 100.0
        )
        resized_balances.balances[token_to_divest_from] *= (
            100 - spread_percentage
        ) / 100.0

    if spread_token_symbol in resized_balances.balances:
        spread_additional_token_balance = spread_additional_token_balance.add(
            resized_balances.balances[spread_token_symbol], fill_value=0
        )
    resized_balances.balances[spread_token_symbol] = spread_additional_token_balance

    return resized_balances


def update_treasury_assets_with_spread_balances(
    treasury: Treasury,
    balances: Balances,
    end: str,
    spread_token_name: str,
    spread_token_symbol: str,
    spread_token_address: str,
    spread_token_usd_quote: float,
) -> Treasury:
    for asset in treasury.assets:
        asset.balance_usd = balances.balances[asset.token_symbol].loc[end]
    try:
        treasury.get_asset(spread_token_symbol)
    except StopIteration:
        treasury.assets.append(
            ERC20(
                token_name=spread_token_name,
                token_symbol=spread_token_symbol,
                token_address=spread_token_address,
                balance_usd=balances.balances[spread_token_symbol].loc[end],
                balance=balances.balances[spread_token_symbol].loc[end]
                / spread_token_usd_quote,
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
    spread_token_symbol: str,
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
        start,
        end,
    )
    spread_token_usd_quote = get_usd_quote(spread_token_symbol, end)
    treasury = update_treasury_assets_with_spread_balances(
        treasury,
        balances,
        end,
        spread_token_name,
        spread_token_symbol,
        spread_token_address,
        spread_token_usd_quote,
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
