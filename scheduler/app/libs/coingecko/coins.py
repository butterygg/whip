from billiard.pool import MaybeEncodingError
from json.decoder import JSONDecodeError
from time import sleep
from typing import Tuple, Union

from httpx import AsyncClient, Timeout

async def get_coin_list():
    async with AsyncClient() as client:
        resp = await client.get("https://api.coingecko.com/api/v3/coins/list?include_platform=true")

        return resp.json()

async def get_coin_hist_price(contract_address: str, symbol: str, start: Union[int, Tuple[int, str]], end: int = None):
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
    timeout = Timeout(read=15.0, connect=30.0)
    async with AsyncClient(
        headers={
            "user-agent":
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36 Edg/100.0.1185.50"\
        }
    ) as client:
        # replace ETH address to WETH
        if contract_address == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
            contract_address = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
        try:
            resp = await client.get(
                f"https://api.coingecko.com/api/v3/coins/ethereum/contract/{contract_address}/market_chart/range?vs_currency=usd&from={start}&to={end}",
                timeout=timeout
                
            )
        except MaybeEncodingError as e:
            sleep(5)
            resp = await client.get(
                f"https://api.coingecko.com/api/v3/coins/ethereum/contract/{contract_address}/market_chart/range?vs_currency=usd&from={start}&to={end}",
                timeout=timeout
            )
        sleep(5)
        try:
            return (contract_address, symbol, resp.json().get("prices"))
        except JSONDecodeError as e:
            print(f"decode error for {resp.url}")
            return None
