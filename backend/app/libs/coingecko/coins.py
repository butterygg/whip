import datetime
import json
from json.decoder import JSONDecodeError
from time import sleep
from typing import Any, Optional

import dateutil.tz
import dateutil.utils
from dateutil.tz import UTC
from httpx import AsyncClient, Timeout

from ... import db
from ..types import Price

COINGECKO_API_URL = "https://api.coingecko.com/api/v3"


CACHE_HASH = "coingecko_hist_prices"
CACHE_KEY_TEMPLATE = "{symbol}_{start}_{end}"


async def _get_data(
    token_address: str, start_date: datetime.datetime, end_date: datetime.datetime
) -> Optional[Any]:
    timeout = Timeout(10.0, read=15.0, connect=30.0)
    async with AsyncClient(
        headers={
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            + "AppleWebKit/537.36 (KHTML, like Gecko) "
            + "Chrome/100.0.4896.127 Safari/537.36 Edg/100.0.1185.50"
        }
    ) as client:
        # replace ETH address to WETH
        if token_address == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
            token_address = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
            resp = await client.get(
                COINGECKO_API_URL
                + f"/coins/ethereum/contract/{token_address}/market_chart/range"
                + f"?vs_currency=usd&from={start_date.timestamp()}&to={end_date.timestamp()}",
                timeout=timeout,
            )
            sleep(5)
            try:
                return resp.json().get("prices")
            except JSONDecodeError:
                print(f"decode error for {resp.url}")
                return None


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
        hist_price_data = await _get_data(token_address, start_date, end_date)
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
