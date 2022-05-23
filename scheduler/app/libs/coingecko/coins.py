from billiard.pool import MaybeEncodingError
from json.decoder import JSONDecodeError
from time import sleep
from typing import Tuple, Union
from httpx import AsyncClient, Timeout
import json

from .. import db


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
    start: Union[int, Tuple[int, str]],
    end: int = None,
) -> Tuple[str, str, List[List[int]]]:
    """ Get the historical quote rates for a given token

        `start` is the start date to query prices from, if
        an `end` date isn't given, it returns the historical
        prices from the `start` date to the present.

        Parameters
        ---
        contract_address: str
            ERC20 Contract address of the token to query
        symbol: str
            ERC20 symbol of token
        start: int | Tuple[int, str]
            start time can either be a unix timestamp in milliseconds
            or a tuple ( # of units, units ) where a unit can be one of:
            "years" | "months" | "days"
        end: int
            end date as unix timestamp in milliseconds

        Notes
        ---
        if `contract_address` is the native token address,
        0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee,
        the it is converted to the WETH address
    """
    if type(start) == tuple:
        from datetime import datetime
        from datetime import timedelta
        from dateutil.utils import today
        from dateutil.tz import UTC
        from time import mktime

        if not end:
            end: datetime = today(UTC)
        else:
            end = datetime.fromtimestamp(end, tz=UTC)
        start: datetime = end - timedelta(days=365 * start[0])
        start = mktime(start.timetuple())
        end = mktime(end.timetuple())

    cache_key = CACHE_KEY_TEMPLATE.format(symbol=symbol, start=start, end=end)
    if db.hexists(CACHE_HASH, cache_key):
        prices = json.loads(db.hget(CACHE_HASH, cache_key))
        return (contract_address, symbol, prices)

    timeout = Timeout(10.0, read=15.0, connect=30.0)
    async with AsyncClient(
        headers={
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                          "AppleWebKit/537.36 (KHTML, like Gecko) " +
                          "Chrome/100.0.4896.127 Safari/537.36 Edg/100.0.1185.50"
        }
    ) as client:
        # replace ETH address to WETH
        if contract_address == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
            contract_address = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
        try:
            resp = await client.get(
                f"https://api.coingecko.com/api/v3/coins/ethereum/"
                    + f"contract/{contract_address}/market_chart/"
                    + f"range?vs_currency=usd&from={start}&to={end}",
                timeout=timeout,
            )
        except MaybeEncodingError as e:
            sleep(5)
            resp = await client.get(
                f"https://api.coingecko.com/api/v3/coins/ethereum/contract/"
                    + f"{contract_address}/market_chart/"
                    + f"range?vs_currency=usd&from={start}&to={end}",
                timeout=timeout,
            )
        sleep(5)
        try:
            prices = resp.json().get("prices")
        except JSONDecodeError as e:
            print(f"decode error for {resp.url}")
            return None

        db.hset(CACHE_HASH, cache_key, json.dumps(prices))

        return (contract_address, symbol, prices)
