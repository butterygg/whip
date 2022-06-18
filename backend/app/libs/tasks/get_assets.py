from asyncio import run
from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import reduce
from json import dumps
from typing import Any, Optional

import pandas as pd
from asgiref.sync import async_to_sync
from celery.schedules import crontab
from celery.utils.log import get_task_logger
from dateutil.tz import UTC
from dateutil.utils import today
from dotenv import load_dotenv
from httpx import ReadTimeout

from ... import db
from ...celery_main import app as celery_app
from .. import bitquery, coingecko, covalent, price_stats, spread
from ..pd_inter_calc import make_daily_hist_balance
from ..series import make_hist_price_series, make_hist_transfer_series
from ..storage_helpers import (
    get_and_store_treasury_list,
    retrieve_treasuries_metadata,
    store_asset_correlations,
    store_asset_hist_balance,
    store_asset_hist_performance,
)
from ..tokenlists import maybe_populate_whitelist, store_and_get_whitelists
from ..types import ERC20, Treasury

load_dotenv()


async def make_treasury(treasury_address: str, chain_id: int) -> Treasury:
    token_whitelist = await maybe_populate_whitelist()
    return await covalent.get_treasury(
        await covalent.get_treasury_portfolio(treasury_address, chain_id),
        token_whitelist,
    )


async def get_token_hist_prices(treasury: Treasury) -> dict[str, pd.Series]:
    asset_addresses_including_eth = {
        (a.token_symbol, a.token_address) for a in treasury.assets
    } | {("ETH", "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")}
    maybe_prices = {
        token_symbol: await coingecko.get_coin_hist_price(token_address, token_symbol)
        for token_symbol, token_address in asset_addresses_including_eth
    }
    return {
        token_symbol: make_hist_price_series(token_symbol, prices)
        for token_symbol, prices in maybe_prices.items()
        if prices
    }


def augment_token_hist_prices(
    token_hist_prices: dict[str, pd.Series]
) -> dict[str, pd.DataFrame]:
    return {
        symbol: price_stats.make_returns_df(token_hist_price, "price")
        for symbol, token_hist_price in token_hist_prices.items()
    }


def filter_out_small_assets(treasury: Treasury):
    treasury.assets = [
        asset
        for asset in treasury.assets
        if asset.balance / treasury.usd_total >= 0.5 / 100
    ]
    return treasury


async def get_asset_transfer_balances(treasury: Treasury) -> dict[str, pd.Series]:
    "Returns series of balances defined at times of assets transfers"
    maybe_transfers = {
        asset.token_symbol: await covalent.get_token_transfers(
            treasury.address, asset.token_address
        )
        for asset in treasury.assets
    }
    maybe_transfers["ETH"] = await bitquery.get_eth_transfers(treasury.address)
    return {
        symbol: make_hist_transfer_series(symbol, transfers)
        for symbol, transfers in maybe_transfers.items()
        if transfers
    }


async def fill_asset_hist_balances(
    asset_transfer_balances: dict[str, pd.Series],
    augmented_token_hist_prices: dict[str, pd.DataFrame],
) -> dict[str, pd.Series]:
    def fill_asset_hist_balance(
        symbol, augmented_token_hist_price
    ) -> Optional[pd.DataFrame]:
        if (
            symbol not in asset_transfer_balances
            or len(asset_transfer_balances[symbol]) < 2
        ):
            return None
        return make_daily_hist_balance(
            symbol, asset_transfer_balances[symbol], augmented_token_hist_price.price
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


def augment_total_balance(asset_hist_balances: dict[str, pd.Series]) -> pd.DataFrame:
    hist_total_balance: pd.Series = reduce(
        lambda acc, item: acc.add(item, fill_value=0),
        asset_hist_balances.values(),
    )
    return price_stats.make_returns_df(hist_total_balance, "balance")


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


async def build_assets(
    treasury: Treasury,
) -> tuple[Treasury, dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    augmented_token_hist_prices = augment_token_hist_prices(
        await get_token_hist_prices(treasury)
    )
    asset_hist_balances = await fill_asset_hist_balances(
        await get_asset_transfer_balances(treasury),
        augmented_token_hist_prices,
    )
    augmented_token_hist_prices = {
        k: v
        for k, v in augmented_token_hist_prices.items()
        if k in asset_hist_balances or k == "ETH"
    }
    treasury.assets = [
        a
        for a in treasury.assets
        if a.token_symbol in augmented_token_hist_prices
        and a.token_symbol in asset_hist_balances
    ]

    return (
        treasury,
        augmented_token_hist_prices,
        asset_hist_balances,
    )


async def build_spread_assets(
    spread_treasury: Treasury,
    start: str,
    end: str,
    spread_token_symbol: str,
    spread_percentage: int,
) -> tuple[Treasury, dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    augmented_token_hist_prices = augment_token_hist_prices(
        await get_token_hist_prices(spread_treasury)
    )
    asset_hist_balances = await fill_asset_hist_balances(
        await get_asset_transfer_balances(spread_treasury),
        augmented_token_hist_prices,
    )
    augmented_token_hist_prices = {
        k: v
        for k, v in augmented_token_hist_prices.items()
        if k in asset_hist_balances or k == "ETH" or k == spread_token_symbol
    }

    spread_asset_hist_balances = spread.apply_spread_to_balances(
        asset_hist_balances,
        spread_token_symbol,
        spread_percentage,
        start,
        end,
    )
    assert next(iter(spread_asset_hist_balances.values())).iloc[0] >= 0

    spread_treasury.assets = [
        a
        for a in spread_treasury.assets
        if (
            a.token_symbol in augmented_token_hist_prices
            and a.token_symbol in spread_asset_hist_balances
        )
        or a.token_symbol == spread_token_symbol
    ]

    return (spread_treasury, augmented_token_hist_prices, spread_asset_hist_balances)


def augment_treasury(
    treasury: Treasury,
    asset_hist_balances: dict[str, pd.Series],
    augmented_token_hist_prices: dict[str, pd.DataFrame],
    start: str,
    end: str,
) -> tuple[Treasury, pd.Series]:
    augmented_total_balance = augment_total_balance(asset_hist_balances)
    augmented_treasury = price_stats.fill_asset_risk_contributions(
        treasury, augmented_token_hist_prices, start, end
    )
    return augmented_treasury, augmented_total_balance


def augment_spread_treasury(
    spread_treasury: Treasury,
    spread_asset_hist_balances: dict[str, pd.Series],
    augmented_token_hist_prices: dict[str, pd.DataFrame],
    start: str,
    end: str,
) -> tuple[Treasury, pd.Series]:
    spread_treasury.usd_total = sum(
        b.loc[end] for b in spread_asset_hist_balances.values()
    )
    assert spread_treasury.usd_total >= 0

    for asset in spread_treasury.assets:
        asset.balance = spread_asset_hist_balances[asset.token_symbol].loc[end]

    augmented_total_balance = augment_total_balance(spread_asset_hist_balances)
    augmented_spread_treasury = price_stats.fill_asset_risk_contributions(
        spread_treasury, augmented_token_hist_prices, start, end
    )
    return (
        augmented_spread_treasury,
        augmented_total_balance,
    )


async def build_treasury_with_assets(
    treasury_address: str, chain_id: int, start: str, end: str
) -> tuple[Treasury, dict[str, pd.DataFrame], dict[str, pd.DataFrame], pd.Series]:
    treasury = await build_bare_treasury(treasury_address, chain_id)

    (
        treasury,
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
) -> tuple[Treasury, dict[str, pd.DataFrame], dict[str, pd.DataFrame], pd.Series]:
    spread_treasury = await build_spread_bare_treasury(
        treasury_address,
        chain_id,
        spread_token_name,
        spread_token_symbol,
        spread_token_address,
        spread_percentage,
    )

    (
        spread_treasury,
        augmented_token_hist_prices,
        spread_asset_hist_balances,
    ) = await build_spread_assets(
        spread_treasury,
        start,
        end,
        spread_token_symbol,
        spread_percentage,
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
        crontab(hour=0, minute=30, nowfun=datetime.now),
        reload_treasuries_stats.s(),
        name="reload treasuries stats",
    )


@celery_app.on_after_finalize.connect
def setup_reload_list(sender, **_):
    sender.add_periodic_task(
        86400.0 * 3, reload_treasuries_list.s(), name="reload treasury list"
    )

    sender.add_periodic_task(
        crontab(hour=0, minute=0, day_of_week=[1], nowfun=datetime.now),
        reload_whitelist.s(),
        name="reload token whitelist",
    )


@celery_app.on_after_finalize.connect
def setup_init_tasks(**_):
    reload_whitelist.apply_async()


LOCK_EXPIRE = 60 * 20  # lock expires in 20 minutes


@contextmanager
def redis_lock(lock_id: str, oid: Any):
    status = db.setnx(lock_id, oid)
    if status:
        db.expire(lock_id, LOCK_EXPIRE)
    yield status


def check_lock(lock_id: str, task_id: str, oid, logger):
    with redis_lock(lock_id, oid) as acquired:
        if not acquired:
            logger.info("task %s already running, revoking...", task_id)
            celery_app.control.revoke(task_id, terminate=True)


def set_new_task(task_id: str):
    db.set("curr_task", task_id)
    if db.ttl("curr_task") <= 0:
        db.expire("curr_task", LOCK_EXPIRE)


@celery_app.task(bind=True)
def reload_treasuries_stats(self):
    logger = get_task_logger(self.request.id)
    check_lock(f"{self.name}-lock", self.request.id, celery_app.oid, logger)
    set_new_task(self.request.id)

    end_date: datetime = today(UTC)
    start_date: datetime = end_date - timedelta(days=365)

    start = start_date.isoformat()[:10]
    end = end_date.isoformat()[:10]

    treasuries = retrieve_treasuries_metadata(db)
    if not treasuries:
        get_and_store_treasury_list(db)
        treasuries = retrieve_treasuries_metadata(db)

    for treasury_metadata in treasuries:
        with db.pipeline() as pipe:
            try:
                (
                    treasury,
                    augmented_token_hist_prices,
                    asset_hist_balances,
                    _,
                ) = async_to_sync(build_treasury_with_assets)(
                    *treasury_metadata, start, end
                )
            except TypeError:
                # This error is likely caused by
                # backend.app.libs.pd_inter_calc.make_daily_hist_balance
                logger.error(  # [FIXME]
                    "error reducing augemented treasury balance for %s",
                    treasury_metadata[0],
                )
                continue
            except ReadTimeout:
                logger.error(
                    "error receiving a covalent portfolio_v2 response for %s, continuing",
                    treasury_metadata[0],
                )
                continue

            for symbol, asset_hist_performance in augmented_token_hist_prices.items():
                store_asset_hist_performance(
                    symbol,
                    dumps(
                        {
                            ts.isoformat(): value
                            for ts, value in asset_hist_performance.to_dict(
                                orient="index"
                            ).items()
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
                price_stats.make_returns_correlations_matrix(
                    treasury, augmented_token_hist_prices, start, end
                ).to_json(orient="index"),
                provider=pipe,
            )

            pipe.execute()


@celery_app.task(bind=True)
def reload_whitelist(self):
    set_new_task(self.request.id)
    try:
        whitelist = run(store_and_get_whitelists())
        assert whitelist
    except AssertionError:
        logger = get_task_logger(self.request.id)
        logger.error("reload whitelist task failed: empty whitelist")


@celery_app.task(bind=True)
def reload_treasuries_list(self):
    set_new_task(self.request.id)
    get_and_store_treasury_list(db)
