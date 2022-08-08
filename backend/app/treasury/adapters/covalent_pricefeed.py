# pylint: disable=duplicate-code
import json
from datetime import datetime, timedelta
from os import getenv
from typing import Any, TypeVar

import dateutil
from celery.utils.log import get_logger
from httpx import AsyncClient, HTTPStatusError, Timeout

from ... import db
from ..models import Price

COVALENT_URI = "https://api.covalenthq.com/v1"
CACHE_HASH_PRICES = "covalent_prices"
CACHE_KEY_TEMPLATE_PRICES = "{symbol}_{start}_{end}"

RawPrices = TypeVar("RawPrices", list[dict[str, Any]], None)


async def _get_pricing_data(
    token_address: str,
    start_date: datetime,
    end_date: datetime,
    chain_id: int = 1,
) -> RawPrices:
    start = start_date.strftime("%Y-%m-%d")
    end = end_date.strftime("%Y-%m-%d")
    timeout = Timeout(10.0, read=15.0, connect=30.0)
    async with AsyncClient(
        headers={
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            + "AppleWebKit/537.36 (KHTML, like Gecko) "
            + "Chrome/100.0.4896.127 Safari/537.36 Edg/100.0.1185.50"
        },
    ) as client:
        if token_address == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
            token_address = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"

        req_url = (
            COVALENT_URI
            + f"/pricing/historical_by_addresses_v2/{chain_id}"
            + f"/USD/{token_address}/?quote-currency=USD&format=JSON"
            + f"&from={start}&to={end}&key=ckey_{getenv('COVALENT_KEY')}"
        )

        resp = await client.get(req_url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()["data"][0]["prices"]


async def get_token_hist_price_covalent(
    token_address: str, token_symbol: str
) -> list[Price]:
    end_date = dateutil.utils.today(dateutil.tz.UTC)
    start_date = end_date - timedelta(days=366)

    cache_key = CACHE_KEY_TEMPLATE_PRICES.format(
        symbol=token_symbol,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
    )
    if db.hexists(CACHE_HASH_PRICES, cache_key):
        hist_price_data = json.loads(db.hget(CACHE_HASH_PRICES, cache_key))
    else:
        try:
            hist_price_data = await _get_pricing_data(
                token_address, start_date, end_date
            )
        except (
            HTTPStatusError,
            json.decoder.JSONDecodeError,
            KeyError,
        ) as error:
            logger = get_logger(__name__)
            if error.__class__ is HTTPStatusError:
                msg = (
                    "unable to receive a Covalent"
                    + "`pricing/historical_by_addresses_v2` API response"
                )
            else:
                msg = "error processing Covalent `pricing/historical_by_addresses_v2` API response"
            logger.error(
                msg,
                exc_info=error,
            )
            return []
        db.hset(CACHE_HASH_PRICES, cache_key, json.dumps(hist_price_data))
        # Set an expiry flag on this hset name for a day.
        # It will only set an expire on this name if none exists for it.
        if db.ttl(CACHE_HASH_PRICES) <= 0:
            time_to_evict = datetime.now(tz=dateutil.tz.UTC) + timedelta(days=1)
            time_to_evict_ts = time_to_evict.replace(
                hour=0, minute=0, second=0, microsecond=0
            ).timestamp()

            db.expireat(CACHE_HASH_PRICES, int(time_to_evict_ts))

    return [
        Price(
            timestamp=dateutil.parser.parse(item["date"]).replace(
                tzinfo=dateutil.tz.UTC
            ),
            value=item["price"],
        )
        for item in hist_price_data
    ]
