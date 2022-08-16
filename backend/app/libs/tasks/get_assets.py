from asyncio import gather, run
from datetime import datetime, timedelta
from json import dumps
from typing import Optional

from asgiref.sync import async_to_sync
from celery.schedules import crontab
from celery.utils.log import get_task_logger
from dateutil.tz import UTC
from dateutil.utils import today
from dotenv import load_dotenv
from httpx import HTTPStatusError, ReadTimeout

from ... import db
from ...celery_main import app as celery_app
from ...token_whitelists import (
    store_and_get_covalent_pairs_whitelist,
    store_and_get_tokenlist_whitelist,
)
from ...treasury import (
    build_treasury_with_assets,
    get_treasury_list,
    remove_treasuries_metadata,
    retrieve_treasuries_metadata,
    store_treasuries_metadata,
)
from .. import price_stats
from .redis import (
    retrieve_troublesome_treasuries,
    store_asset_correlations,
    store_asset_hist_balance,
    store_asset_hist_performance,
    store_troublesome_treasuries,
)

load_dotenv()


@celery_app.on_after_finalize.connect
def setup_init_tasks(sender, **_):
    sender.send_task("tasks.reload_whitelist")

    sender.add_periodic_task(
        crontab(hour=0, minute=30, nowfun=datetime.utcnow),
        reload_treasuries_stats.s(),
        name="reload treasuries stats",
    )

    sender.add_periodic_task(
        crontab(
            hour=1, minute=0, day_of_week=[0], day_of_month="14", nowfun=datetime.utcnow
        ),
        reload_treasuries_list.s(),
        name="reload treasury list",
    )

    sender.add_periodic_task(
        crontab(hour=0, minute=0, nowfun=datetime.utcnow),
        reload_whitelist.s(),
        name="reload token whitelist",
    )

    sender.add_periodic_task(
        crontab(minute=0, hour="*/1", nowfun=datetime.utcnow),
        retry_troublesome_treasuries.s(),
        name="Retry `reload_treasuries_stats` on treasuries which have timed out",
    )


@celery_app.task(name="tasks.reload_treasuries_stats")
def reload_treasuries_stats(
    troublesome_treasuries: Optional[set[tuple[str, int]]] = None
):
    logger = get_task_logger(__name__)

    end_date: datetime = today(UTC)
    start_date: datetime = end_date - timedelta(days=365)

    start = start_date.isoformat()[:10]
    end = end_date.isoformat()[:10]

    treasuries = (
        troublesome_treasuries
        if troublesome_treasuries
        else retrieve_treasuries_metadata(db)
    )
    if not treasuries:
        store_treasuries_metadata(db, get_treasury_list())
        treasuries = retrieve_treasuries_metadata(db)

    candidate_troublesome_treasuries: set[tuple[str, int]] = set()

    for treasury_metadata in treasuries:
        with db.pipeline() as pipe:
            try:
                (
                    treasury,
                    augmented_token_hist_prices,
                    asset_hist_balances,
                    _,
                ) = async_to_sync(build_treasury_with_assets)(
                    (treasury_metadata, start, end)
                )
            except TypeError:
                # This currently only raises when the given treasury has no balance
                logger.error(  # [FIXME]
                    "error reducing augemented treasury balance for %s",
                    treasury_metadata[0],
                )
                continue
            except (ReadTimeout, HTTPStatusError):
                error_msg = "error receiving a covalent response for %s, continuing"
                logger.error(
                    error_msg,
                    treasury_metadata[0],
                )
                candidate_troublesome_treasuries.add(treasury_metadata)
                continue

            for (
                symbol,
                asset_hist_performance,
            ) in augmented_token_hist_prices.prices.items():
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

            for symbol, asset_hist_balance in asset_hist_balances.usd_balances.items():
                store_asset_hist_balance(
                    treasury.address,
                    symbol,
                    asset_hist_balance.to_json(orient="records"),
                    provider=pipe,
                )

            store_asset_correlations(
                treasury.address,
                price_stats.make_returns_correlations_matrix(
                    augmented_token_hist_prices.prices, start, end
                ).to_json(orient="index"),
                provider=pipe,
            )

            pipe.execute()

    if candidate_troublesome_treasuries:
        store_troublesome_treasuries(candidate_troublesome_treasuries, provider=db)


async def gather_all_whitelists() -> tuple[list[str]]:
    return await gather(
        store_and_get_tokenlist_whitelist(db),
        store_and_get_covalent_pairs_whitelist(db),
    )


@celery_app.task(name="tasks.reload_whitelist")
def reload_whitelist():
    try:
        whitelist = run(gather_all_whitelists())
        assert whitelist
    except AssertionError:
        logger = get_task_logger(__name__)
        logger.error("reload whitelist task failed: empty whitelist")


@celery_app.task(name="tasks.reload_treasuries_list")
def reload_treasuries_list():
    remove_treasuries_metadata(db)
    store_treasuries_metadata(db, get_treasury_list())


@celery_app.task(name="tasks.retry_troublesome_treasuries")
def retry_troublesome_treasuries():
    troublesome_treasuries = retrieve_troublesome_treasuries(db)
    if troublesome_treasuries:
        reload_treasuries_stats(troublesome_treasuries)
