import datetime
import json
from json.decoder import JSONDecodeError
from time import sleep
from typing import Any, Coroutine, Optional, TypeVar, Union

import dateutil.tz
import dateutil.utils
from celery.utils.log import get_task_logger
from dateutil.tz import UTC
from httpx import AsyncClient, HTTPStatusError, Timeout

from ... import db
from ..types import Price

COINGECKO_API_URL = "https://api.coingecko.com/api/v3"


CACHE_HASH = "coingecko_hist_prices"
CACHE_KEY_TEMPLATE = "{symbol}_{start}_{end}"


RawPrices = TypeVar("RawPrices", list[list[Union[int, float]]], list[Any])


async def retry(method: Coroutine, url: str) -> Optional[RawPrices]:
    sleep(60)
    resp = await method(url)
    resp.raise_for_status()

    prices = resp.json().get("prices")

    return prices if prices else []


async def _get_data(
    token_address: str, start_date: datetime.datetime, end_date: datetime.datetime
) -> Optional[RawPrices]:
    timeout = Timeout(10.0, read=15.0, connect=30.0)
    async with AsyncClient(
        headers={
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            + "AppleWebKit/537.36 (KHTML, like Gecko) "
            + "Chrome/100.0.4896.127 Safari/537.36 Edg/100.0.1185.50"
        }
    ) as client:
        # replace ETH address with WETH address
        if token_address == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
            token_address = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
        req_url = COINGECKO_API_URL \
            + f"/coins/ethereum/contract/{token_address}/market_chart/range" \
            + f"?vs_currency=usd&from={start_date.timestamp()}&to={end_date.timestamp()}"
        resp = await client.get(
            req_url,
            timeout=timeout,
        )
        resp.raise_for_status()
        resp_data = resp.text
        if "limit" in resp_data or "Limit" in resp_data:
            prices = await retry(client.get, req_url)
        else:
            prices: Optional[RawPrices] = resp.json().get("prices")
        return prices if prices else []


async def get_data(
    token_address: str, start_date: datetime.datetime, end_date: datetime.datetime
) -> Optional[RawPrices]:
    try:
        return await _get_data(token_address, start_date, end_date)
    except (HTTPStatusError, JSONDecodeError) as error:
        logger = get_task_logger(__name__)
        if error.__class__ is HTTPStatusError:
            logger.error(
                "unable to receive a Coingecko `coins` API response",
                exc_info=error,
            )
            return []
        logger.error("error processing Coingecko `coins` API response", exc_info=error)
        return []


# tuple[str, str, list[tuple[int, float]]]
# pd.to_datetime(datetime.datetime.fromtimestamp(int(timestamp / 1000), tz=UTC))
async def get_coin_hist_price(
    token_address: str,
    token_symbol: str,
) -> Optional[list[Price]]:
    end_date = dateutil.utils.today(dateutil.tz.UTC)
    start_date = end_date - datetime.timedelta(days=366)

    cache_key = CACHE_KEY_TEMPLATE.format(
        symbol=token_symbol,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
    )
    if db.hexists(CACHE_HASH, cache_key):
        hist_price_data = json.loads(db.hget(CACHE_HASH, cache_key))

    else:
        hist_price_data = await get_data(token_address, start_date, end_date)
        db.hset(CACHE_HASH, cache_key, json.dumps(hist_price_data))
        # Set an expiry flag on this hset name for a day.
        # It will only set an expire on this name if none exists for it.
        if db.ttl(CACHE_HASH) <= 0:
            db.expire(CACHE_HASH, 86400)

    if hist_price_data is None:
        return None

    return [
        Price(
            timestamp=datetime.datetime.fromtimestamp(int(epoch_time / 1000), tz=UTC),
            value=price,
        )
        for epoch_time, price in hist_price_data
    ]
