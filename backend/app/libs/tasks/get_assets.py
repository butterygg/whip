from asyncio import run
from datetime import datetime, timedelta
from json import dumps

from asgiref.sync import async_to_sync
from celery.schedules import crontab
from celery.utils.log import get_task_logger
from dateutil.tz import UTC
from dateutil.utils import today
from dotenv import load_dotenv

from ... import db
from ...celery_main import app as celery_app
from ...treasury import build_treasury_with_assets
from .. import price_stats
from ..storage_helpers import (
    retrieve_treasuries_metadata,
    store_asset_correlations,
    store_asset_hist_balance,
    store_asset_hist_performance,
)
from ..tokenlists import store_and_get_whitelists

load_dotenv()


@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **_):
    sender.add_periodic_task(
        crontab(hour=0, minute=30, nowfun=datetime.now),
        reload_treasuries_data.s(),
        name="reload treasuries data",
    )

    sender.add_periodic_task(
        crontab(hour=0, minute=0, day_of_week=[1], nowfun=datetime.now),
        reload_whitelist.s(),
        name="reload token whitelist",
    )


@celery_app.on_after_finalize.connect
def setup_init_tasks(**_):
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
                price_stats.make_returns_correlations_matrix(
                    augmented_token_hist_prices, start, end
                ).to_json(orient="index"),
                provider=pipe,
            )

            pipe.execute()


@celery_app.task(bind=True)
def reload_whitelist(self):
    try:
        whitelist = run(store_and_get_whitelists())
        assert whitelist
    except AssertionError:
        logger = get_task_logger(self.request.id)
        logger.error("reload whitelist task failed: empty whitelist")
