# from asyncio import gather
from functools import reduce

import pandas as pd

from ..libs import price_stats
from ..treasury import (
    Balances,
    Prices,
    make_balances_from_treasury_and_prices,
    make_prices_from_tokens,
    make_total_balance_from_balances,
    make_treasury_from_address,
)
from .models import MultiTreasury


async def make_multitreasury_from_name(name: str):
    # [XXX] - Move to an HTTP call through an adapter
    _treasury_address_and_chainid = {
        "Gitcoin": (
            [
                "0x57a8865cfB1eCEf7253c27da6B4BC3dAEE5Be518",
                "0xde21F729137C5Af1b01d73aF1dC21eFfa2B8a0d6",
                # "0x44aa9c5a034c1499ec27906e2d427b704b567ffe",
            ],
            1,
        )
    }
    addresses, chain_id = _treasury_address_and_chainid[name]
    # treasuries = await gather(
    #     *(make_treasury_from_address(a, chain_id) for a in addresses)
    # )
    treasuries = [await make_treasury_from_address(a, chain_id) for a in addresses]
    return MultiTreasury.from_treasuries(treasuries)


async def make_balances_from_addresses_and_prices(
    addresses: list[str],
    token_symbols_and_addresses: set[tuple[str, str]],
    prices: Prices,
):
    #     flattened_balances = [
    #         (token_symbol, b)
    #         for token_symbol, balances in await gather(
    #             *(
    #                 make_balances_from_treasury_and_prices(
    #                     a, token_symbols_and_addresses, prices
    #                 )
    #                 for a in addresses
    #             )
    #         ).balances.items()
    #         for b in balances
    #     ]
    balances_list = [
        await make_balances_from_treasury_and_prices(
            a, token_symbols_and_addresses, prices
        )
        for a in addresses
    ]
    flattened_balances = [
        (token_symbol, histbal)
        for balances in balances_list
        for token_symbol, histbal in balances.balances.items()
    ]

    def reducer(
        balances_accumulator: dict[str, pd.Series],
        symbol_and_histbal: tuple[str, pd.Series],
    ) -> dict[str, pd.Series]:
        token_symbol, histbal = symbol_and_histbal
        try:
            existing_histbal = balances_accumulator[token_symbol]
        except KeyError:
            return {**balances_accumulator, token_symbol: histbal}
        else:
            merged_histbal = existing_histbal.add(histbal, fill_value=0)
            return {**balances_accumulator, token_symbol: merged_histbal}

    balances_dict = reduce(reducer, flattened_balances, dict())
    return Balances(balances=balances_dict)


async def update_multitreasury_assets_from_whitelist(
    multitreasury: MultiTreasury, token_symbol_whitelist: set[str]
) -> MultiTreasury:
    multitreasury.assets = [
        a
        for token_symbol, a in multitreasury.assets.items()
        if token_symbol in token_symbol_whitelist
    ]
    return multitreasury


async def update_multitreasury_assets_risk_contributions(
    multitreasury: MultiTreasury,
    prices: Prices,
    start: str,
    end: str,
) -> MultiTreasury:
    returns_and_balances = {
        token_symbol: (prices.prices[token_symbol], asset.balance)
        for token_symbol, asset in multitreasury.assets.items()
    }
    for symbol, risk_contribution in price_stats.calculate_risk_contributions(
        returns_and_balances, start, end
    ).items():
        multitreasury.get_asset(symbol).risk_contribution = risk_contribution
    return multitreasury


async def build_multitreasury_with_assets(treasury_name: str, start: str, end: str):
    multitreasury = await make_multitreasury_from_name(treasury_name)

    token_symbols_and_addresses: set[tuple[str, str]] = {
        (token_symbol, asset.token_address)
        for token_symbol, asset in multitreasury.assets.items()
    }

    prices = await make_prices_from_tokens(token_symbols_and_addresses)

    balances = await make_balances_from_addresses_and_prices(
        multitreasury.addresses, token_symbols_and_addresses, prices
    )

    multitreasury = update_multitreasury_assets_from_whitelist(
        multitreasury,
        prices.get_existing_token_symbols() | balances.get_existing_token_symbols(),
    )

    total_balance = make_total_balance_from_balances(balances)

    multitreasury = update_multitreasury_assets_risk_contributions(
        multitreasury,
        prices,
        start,
        end,
    )

    return (
        multitreasury,
        prices,
        balances,
        total_balance,
    )
