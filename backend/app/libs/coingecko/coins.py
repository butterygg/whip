import datetime
import json
from json.decoder import JSONDecodeError
from time import sleep

import dateutil.tz
import dateutil.utils
from billiard.pool import MaybeEncodingError
from httpx import AsyncClient, Timeout

from ... import db

COINGECKO_API_URL = "https://api.coingecko.com/api/v3"


async def get_coin_list():
    async with AsyncClient() as client:
        resp = await client.get(
            "https://api.coingecko.com/api/v3/coins/list?include_platform=true"
        )

        return resp.json()


CACHE_HASH = "coingecko_hist_prices"
CACHE_KEY_TEMPLATE = "{symbol}_{start}_{end}"


async def get_coin_hist_price(
    contract_address: str,
    symbol: str,
):
    end_date = dateutil.utils.today(dateutil.tz.UTC)
    start_date = end_date - datetime.timedelta(days=366)

    cache_key = CACHE_KEY_TEMPLATE.format(
        symbol=symbol,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
    )
    if db.hexists(CACHE_HASH, cache_key):
        prices = json.loads(db.hget(CACHE_HASH, cache_key))
        if prices is not None:
            return (contract_address, symbol, prices)
        return None

    timeout = Timeout(10.0, read=15.0, connect=30.0)
    async with AsyncClient(
        headers={
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            + "AppleWebKit/537.36 (KHTML, like Gecko) "
            + "Chrome/100.0.4896.127 Safari/537.36 Edg/100.0.1185.50"
        }
    ) as client:
        # replace ETH address to WETH
        if contract_address == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
            contract_address = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
        try:
            resp = await client.get(
                COINGECKO_API_URL
                + f"/coins/ethereum/contract/{contract_address}/market_chart/range"
                + f"?vs_currency=usd&from={start_date.timestamp()}&to={end_date.timestamp()}",
                timeout=timeout,
            )
        except MaybeEncodingError:
            sleep(5)
            resp = await client.get(
                COINGECKO_API_URL
                + f"/coins/ethereum/contract/{contract_address}/market_chart/range"
                + f"?vs_currency=usd&from={start_date.timestamp()}&to={end_date.timestamp()}",
                timeout=timeout,
            )
        sleep(5)
        try:
            prices = resp.json().get("prices")
            if prices is None:
                return None
        except JSONDecodeError:
            print(f"decode error for {resp.url}")
            return None

    db.hset(CACHE_HASH, cache_key, json.dumps(prices))

    return (contract_address, symbol, prices)
