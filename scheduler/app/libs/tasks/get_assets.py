from datetime import datetime
from functools import reduce
from json import dumps
from typing import Any

from asgiref.sync import async_to_sync
from dotenv import load_dotenv
from pandas import DataFrame as DF, Series, to_datetime

from .. import bitquery
from ..storage_helpers import (
    store_asset_hist_balance,
    store_asset_hist_performance,
    retrieve_treasuries_metadata
)
from . import db, celery_app
from ..pd_inter_calc import portfolio_midnight_filler
from ..types import Treasury
from .. import coingecko
from .. import covalent
from .treasury_ops import (
    add_statistics,
    populate_bitquery_hist_eth_balance,
    populate_hist_tres_balance,
    calculate_risk_contributions,
)

load_dotenv()


async def make_treasury(treasury_address: str, chain_id: int) -> Treasury:
    return await covalent.get_treasury(
        await covalent.get_treasury_portfolio(treasury_address, chain_id)
    )


async def get_token_hist_prices(treasury: Treasury) -> dict[str, DF]:
    asset_addresses_including_ETH = {
        (a.token_symbol, a.token_address) for a in treasury.assets
    } | {("ETH", "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")}
    maybe_hist_prices = {
        token_symbol: await coingecko.get_coin_hist_price(token_address, token_symbol)
        for token_symbol, token_address in asset_addresses_including_ETH
    }
    hist_prices = {
        symbol: mhp for symbol, mhp in maybe_hist_prices.items() if mhp is not None
    }
    return {
        symbol: coingecko.coingecko_hist_df(addr, symbol, prices)
        for symbol, (addr, symbol, prices) in hist_prices.items()
        if prices
    }


def augment_token_hist_prices(
    token_hist_prices: dict[str, DF]
) -> dict[str, DF]:
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
    def fill_asset_hist_balance(symbol, augmented_token_hist_price):
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


def augment_total_balance(
    treasury: Treasury, asset_hist_balances: dict[str, DF]
) -> Series:
    hist_total_balance = reduce(
        lambda acc, item: acc.add(item, fill_value=0),
        (balance["balance"] for balance in asset_hist_balances.values()),
    )
    return add_statistics(
        hist_total_balance, column_name="balance", reverse=False, index="timestamp"
    )


async def build_treasury_with_assets(
    treasury_address: str, chain_id: int, start: str = None, end: str = None
) -> tuple[Treasury, dict[str, DF], dict[str, DF]]:
    treasury = filter_out_small_assets(await make_treasury(treasury_address, chain_id))
    augmented_token_hist_prices = augment_token_hist_prices(
        await get_token_hist_prices(treasury)
    )

    if not start:
        from datetime import datetime
        from datetime import timedelta
        from dateutil.utils import today
        from dateutil.tz import UTC
        from time import mktime
        if not end:
            end: datetime = today(UTC)
        else:
            end = datetime.fromisoformat(end, tz=UTC)
        start: datetime = end - timedelta(days=365 * 1)

        start = start.isoformat()
        end = end.isoformat()

    asset_hist_balances = await fill_asset_hist_balances(
        await get_sparse_asset_hist_balances(treasury),
        augmented_token_hist_prices,
    )
    augmented_total_balance = augment_total_balance(treasury, asset_hist_balances)
    treasury = calculate_risk_contributions(
        treasury, augmented_token_hist_prices, start, end
    )
    augmented_token_hist_prices = {
        symbol: {
            ts.isoformat(): value
            for ts, value in
            hist_prices.set_index("timestamp").to_dict(orient="index").items()
        }
        for symbol, hist_prices in augmented_token_hist_prices.items()
    }
    return (
        treasury,
        augmented_token_hist_prices,
        asset_hist_balances,
        augmented_total_balance,
    )


@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        30.0, reload_treasuries_data.s(), name="reload treasuries data"
    )


@celery_app.task
def reload_treasuries_data():
    for treasury_metadata in retrieve_treasuries_metadata():
        with db.pipeline() as pipe:
            treasury, \
            augmented_token_hist_prices, \
            asset_hist_balances, \
            augemented_total_balance \
                = async_to_sync(
                build_treasury_with_assets
            )(*treasury_metadata)

            for symbol, asset_hist_performance in augmented_token_hist_prices.items():
                store_asset_hist_performance(
                    symbol,
                    dumps(asset_hist_performance),
                    pipe
                )

            for symbol, asset_hist_balance in asset_hist_balances.items():
                store_asset_hist_balance(
                    treasury.address,
                    symbol,
                    asset_hist_balance.to_json(orient="records"),
                    provider=pipe,
                )
            pipe.execute()
