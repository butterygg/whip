from asyncio import run
from datetime import datetime, timedelta
from functools import reduce
from json import dumps
from typing import Optional

from asgiref.sync import async_to_sync
from dateutil.tz import UTC
from dateutil.utils import today
from dotenv import load_dotenv
from pandas import DataFrame as DF
from pandas import Series, to_datetime

from ... import db
from ...celery_main import app as celery_app
from .. import bitquery, coingecko, covalent
from ..pd_inter_calc import portfolio_midnight_filler
from ..storage_helpers import (
    retrieve_treasuries_metadata,
    store_asset_correlations,
    store_asset_hist_balance,
    store_asset_hist_performance,
)
from ..tokenlists import get_all_token_lists, maybe_populate_whitelist
from ..types import ERC20, Treasury
from .treasury_ops import (
    add_statistics,
    apply_spread_percentages,
    calculate_correlations,
    calculate_risk_contributions,
    populate_bitquery_hist_eth_balance,
    populate_hist_tres_balance,
)

load_dotenv()


async def make_treasury(treasury_address: str, chain_id: int) -> Treasury:
    token_whitelist = await maybe_populate_whitelist()
    return await covalent.get_treasury(
        await covalent.get_treasury_portfolio(treasury_address, chain_id),
        token_whitelist,
    )


async def get_token_hist_prices(treasury: Treasury) -> dict[str, DF]:
    asset_addresses_including_eth = {
        (a.token_symbol, a.token_address) for a in treasury.assets
    } | {("ETH", "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")}
    maybe_hist_prices = {}
    for token_symbol, token_address in asset_addresses_including_eth:
        maybe_hist_price = await coingecko.get_coin_hist_price(
            token_address, token_symbol
        )
        if not maybe_hist_price:
            treasury.prune(token_symbol)
            continue
        maybe_hist_prices.update({token_symbol: maybe_hist_price})

    hist_prices = {
        symbol: mhp for symbol, mhp in maybe_hist_prices.items() if mhp is not None
    }
    return {
        symbol: coingecko.coingecko_hist_df(addr, symbol, prices)
        for symbol, (addr, symbol, prices) in hist_prices.items()
        if prices
    }


def augment_token_hist_prices(token_hist_prices: dict[str, DF]) -> dict[str, DF]:
    return {
        symbol: add_statistics(token_hist_price)
        for symbol, token_hist_price in token_hist_prices.items()
    }


def filter_out_small_assets(treasury: Treasury):
    treasury.assets = [
        asset
        for asset in treasury.assets
        if asset.balance / treasury.usd_total >= 0.5 / 100
    ]
    return treasury


async def get_sparse_asset_hist_balances(treasury: Treasury) -> dict[str, Series]:
    asset_contract_addresses = {
        asset.token_symbol: asset.token_address for asset in treasury.assets
    }
    transfer_histories = {
        symbol: await covalent.get_token_transfers_for_wallet(
            treasury.address, asset_contract_address
        )
        for symbol, asset_contract_address in asset_contract_addresses.items()
    }
    maybe_sparse_asset_hist_balances = {
        symbol: await populate_hist_tres_balance(transfer_history)
        for symbol, transfer_history in transfer_histories.items()
    }
    maybe_sparse_asset_hist_balances["ETH"] = populate_bitquery_hist_eth_balance(
        await bitquery.get_eth_transactions(treasury.address)
    )
    return {
        symbol: hist
        for symbol, hist in maybe_sparse_asset_hist_balances.items()
        if hist is not None and not hist.empty
    }


async def fill_asset_hist_balances(
    sparse_asset_hist_balances: dict[str, Series],
    augmented_token_hist_prices: dict[str, DF],
) -> dict[str, DF]:
    def fill_asset_hist_balance(symbol, augmented_token_hist_price) -> Optional[DF]:
        if (
            symbol not in sparse_asset_hist_balances
            or len(sparse_asset_hist_balances[symbol]) < 2
        ):
            return None
        quote_rates = Series(data=augmented_token_hist_price["price"])
        quote_rates.index = to_datetime(augmented_token_hist_price["timestamp"])
        quote_rates = quote_rates.iloc[::-1]
        return portfolio_midnight_filler(
            sparse_asset_hist_balances[symbol], quote_rates
        )

    maybe_asset_hist_balance = {
        symbol: fill_asset_hist_balance(symbol, augmented_token_hist_price)
        for symbol, augmented_token_hist_price in augmented_token_hist_prices.items()
    }
    return {
        symbol: asset_hist_balance
        for symbol, asset_hist_balance in maybe_asset_hist_balance.items()
        if asset_hist_balance is not None
    }


def augment_total_balance(asset_hist_balances: dict[str, DF]) -> Series:
    hist_total_balance = reduce(
        lambda acc, item: acc.add(item, fill_value=0),
        (balance["balance"] for balance in asset_hist_balances.values()),
    )
    return add_statistics(
        hist_total_balance, column_name="balance", reverse=False, index="timestamp"
    )


async def build_bare_treasury(treasury_address: str, chain_id: int) -> Treasury:
    return filter_out_small_assets(await make_treasury(treasury_address, chain_id))


async def build_spread_bare_treasury(
    treasury_address: str,
    chain_id: int,
    spread_token_name: str,
    spread_token_symbol: str,
    spread_token_address: str,
    spread_percentage: int,
) -> Treasury:
    treasury = await build_bare_treasury(treasury_address, chain_id)
    try:
        spread_asset = next(
            a for a in treasury.assets if a.token_symbol == spread_token_symbol
        )
    except StopIteration:
        treasury.assets.append(
            ERC20(
                token_name=spread_token_name,
                token_symbol=spread_token_symbol,
                token_address=spread_token_address,
                balance=treasury.usd_total * spread_percentage / 100.0,
            )
        )
    else:
        spread_asset.balance *= spread_percentage / 100.0

    for asset in (a for a in treasury.assets if a.token_symbol != spread_token_symbol):
        asset.balance *= (100 - spread_percentage) / 100.0
    return treasury


async def build_assets(treasury: Treasury) -> tuple[dict[str, DF], dict[str, DF]]:
    augmented_token_hist_prices = augment_token_hist_prices(
        await get_token_hist_prices(treasury)
    )
    asset_hist_balances = await fill_asset_hist_balances(
        await get_sparse_asset_hist_balances(treasury),
        augmented_token_hist_prices,
    )
    return (
        augmented_token_hist_prices,
        asset_hist_balances,
    )


async def build_spread_assets(
    spread_treasury: Treasury,
    start: str,
    spread_token_symbol: str,
    spread_percentage: int,
) -> tuple[dict[str, DF], dict[str, DF]]:
    augmented_token_hist_prices = augment_token_hist_prices(
        await get_token_hist_prices(spread_treasury)
    )
    asset_hist_balances = await fill_asset_hist_balances(
        await get_sparse_asset_hist_balances(spread_treasury),
        augmented_token_hist_prices,
    )

    spread_asset_hist_balances = apply_spread_percentages(
        asset_hist_balances, spread_token_symbol, spread_percentage, start
    )

    return (augmented_token_hist_prices, spread_asset_hist_balances)


def augment_treasury(
    treasury: Treasury,
    asset_hist_balances: dict[str, DF],
    augmented_token_hist_prices: dict[str, DF],
    start: str,
    end: str,
) -> tuple[Treasury, Series]:
    augmented_total_balance = augment_total_balance(asset_hist_balances)
    augmented_treasury = calculate_risk_contributions(
        treasury, augmented_token_hist_prices, start, end
    )
    return augmented_treasury, augmented_total_balance


def augment_spread_treasury(
    spread_treasury: Treasury,
    spread_asset_hist_balances: dict[str, DF],
    augmented_token_hist_prices: dict[str, DF],
    start: str,
    end: str,
) -> tuple[Treasury, Series]:
    spread_treasury.usd_total = sum(
        b.loc[end].balance for b in spread_asset_hist_balances.values()
    )
    for asset in spread_treasury.assets:
        asset.balance = spread_asset_hist_balances[asset.token_symbol].loc[end].balance

    augmented_total_balance = augment_total_balance(spread_asset_hist_balances)
    augmented_spread_treasury = calculate_risk_contributions(
        spread_treasury, augmented_token_hist_prices, start, end
    )
    return (
        augmented_spread_treasury,
        augmented_total_balance,
    )


async def build_treasury_with_assets(
    treasury_address: str, chain_id: int, start: str, end: str
) -> tuple[Treasury, dict[str, DF], dict[str, DF], Series]:
    treasury = await build_bare_treasury(treasury_address, chain_id)

    (
        augmented_token_hist_prices,
        asset_hist_balances,
    ) = await build_assets(treasury)

    augmented_treasury, augmented_total_balance = augment_treasury(
        treasury, asset_hist_balances, augmented_token_hist_prices, start, end
    )
    return (
        augmented_treasury,
        augmented_token_hist_prices,
        asset_hist_balances,
        augmented_total_balance,
    )


async def build_spread_treasury_with_assets(
    treasury_address: str,
    chain_id: int,
    start: str,
    end: str,
    spread_token_name: str,
    spread_token_symbol: str,
    spread_token_address: str,
    spread_percentage: int,
) -> tuple[Treasury, dict[str, DF], dict[str, DF], Series]:
    spread_treasury = await build_spread_bare_treasury(
        treasury_address,
        chain_id,
        spread_token_name,
        spread_token_symbol,
        spread_token_address,
        spread_percentage,
    )

    (
        augmented_token_hist_prices,
        spread_asset_hist_balances,
    ) = await build_spread_assets(
        spread_treasury, start, spread_token_symbol, spread_percentage
    )

    augmented_spread_treasury, augmented_total_balance = augment_spread_treasury(
        spread_treasury,
        spread_asset_hist_balances,
        augmented_token_hist_prices,
        start,
        end,
    )

    return (
        augmented_spread_treasury,
        augmented_token_hist_prices,
        spread_asset_hist_balances,
        augmented_total_balance,
    )


@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **_):
    sender.add_periodic_task(
        30.0, reload_treasuries_data.s(), name="reload treasuries data"
    )


@celery_app.on_after_finalize.connect
def start_whitelist_reload(**_):
    reload_whitelist.apply_async()


@celery_app.task
def reload_treasuries_data():
    end_date: datetime = today(UTC)
    start_date: datetime = end_date - timedelta(days=365)

    start = start_date.isoformat()[:10]
    end = end_date.isoformat()[:10]

    for treasury_metadata in retrieve_treasuries_metadata():
        with db.pipeline() as pipe:
            (
                treasury,
                augmented_token_hist_prices,
                asset_hist_balances,
                _,
            ) = async_to_sync(build_treasury_with_assets)(
                *treasury_metadata, start, end
            )

            for symbol, asset_hist_performance in augmented_token_hist_prices.items():
                store_asset_hist_performance(
                    symbol,
                    dumps(
                        {
                            ts.isoformat(): value
                            for ts, value in asset_hist_performance.set_index(
                                "timestamp"
                            )
                            .to_dict(orient="index")
                            .items()
                        }
                    ),
                    pipe,
                )

            for symbol, asset_hist_balance in asset_hist_balances.items():
                store_asset_hist_balance(
                    treasury.address,
                    symbol,
                    asset_hist_balance.to_json(orient="records"),
                    provider=pipe,
                )

            store_asset_correlations(
                treasury.address,
                calculate_correlations(
                    treasury, augmented_token_hist_prices, start, end
                ).to_json(orient="index"),
                provider=pipe,
            )

            pipe.execute()


@celery_app.task
def reload_whitelist():
    run(get_all_token_lists())
