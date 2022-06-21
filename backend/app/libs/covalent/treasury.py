# pylint: disable=duplicate-code
import json
from asyncio import sleep
from logging import getLogger
from os import getenv
from typing import Any, Coroutine, Dict, List, Optional

from billiard.pool import MaybeEncodingError
import dateutil
from celery.utils.log import get_task_logger
from httpx import AsyncClient, Timeout
from pytz import UTC

from ... import db
from ..types import ERC20, HistoricalPrice, Quote, Treasury

CACHE_HASH = "covalent_treasury"
CACHE_KEY_TEMPLATE = "{address}_{chain_id}_{date}"


async def retry(method: Coroutine, url: str, await_time: float):
    await sleep(await_time)
    await method(url)


async def get_treasury_portfolio(
    treasury_address: str, chain_id: Optional[int] = 1
) -> Dict[str, Any]:
    task_id = db.get("curr_task")
    logger = get_task_logger(task_id) if task_id else getLogger(__name__)
    cache_date = dateutil.utils.today(UTC).strftime("%Y-%m-%d")
    cache_key = CACHE_KEY_TEMPLATE.format(
        address=treasury_address, chain_id=chain_id, date=cache_date
    )
    if db.hexists(CACHE_HASH, cache_key):
        return json.loads(db.hget(CACHE_HASH, cache_key))

    timeout = Timeout(10.0, read=30.0, connect=45.0)
    async with AsyncClient(timeout=timeout) as client:
        url = (
            f"https://api.covalenthq.com/v1/{chain_id}/address/{treasury_address}/"
            + f"portfolio_v2/?&key=ckey_{getenv('COVALENT_KEY')}"
        )
        try:
            resp = await client.get(url)

            data = resp.json()["data"]
        except MaybeEncodingError:
            _msg = "unable to get a response from %s, retrying..."
            logger.warning(_msg, url)
            await retry(client.get, url, 10.0)

    db.hset(CACHE_HASH, cache_key, json.dumps(data))

    return data


async def get_treasury(portfolio: Dict[str, Any], whitelist: list[str]) -> Treasury:

    windows: List[HistoricalPrice] = []
    for item in portfolio["items"]:
        windows.append(
            HistoricalPrice(
                item["contract_address"],
                item["contract_name"],
                item["contract_ticker_symbol"],
                [
                    Quote(
                        dateutil.parser.parse(holding["timestamp"]),
                        holding["quote_rate"],
                    )
                    for holding in item["holdings"]
                ],
            )
        )

    # Certain tokens a treasury may hold are noted as spam.
    # To prevent these tokens from corrupting the data,
    # we filter them out via a whitelist provided by tokenlists.org
    assets = [
        ERC20(
            item["contract_name"],
            item["contract_ticker_symbol"],
            item["contract_address"],
            item["holdings"][0]["close"]["quote"],
        )
        for item in portfolio["items"]
        if item["holdings"][0]["close"]["quote"]
        and item["contract_address"] in whitelist
        and item["holdings"]
    ]

    return Treasury(portfolio["address"], assets, windows)
