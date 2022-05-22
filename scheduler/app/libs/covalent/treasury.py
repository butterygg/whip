import json
import dateutil
from os import getenv
from typing import Any, Dict, List, Optional
from httpx import AsyncClient, Timeout
from pytz import UTC

from .. import db
from ..types import ERC20, Quote, Treasury, HistoricalPrice

CACHE_HASH = "covalent_treasury"
CACHE_KEY_TEMPLATE = "{address}_{chain_id}_{date}"


async def get_treasury_portfolio(
    treasury_address: str, chain_id: Optional[int] = 1
) -> Dict[str, Any]:
    cache_date = dateutil.utils.today(UTC).strftime("%Y-%m-%d")
    cache_key = CACHE_KEY_TEMPLATE.format(
        address=treasury_address, chain_id=chain_id, date=cache_date
    )
    if db.hexists(CACHE_HASH, cache_key):
        return json.loads(db.hget(CACHE_HASH, cache_key))

    timeout = Timeout(10.0, read=15.0, connect=30.0)
    async with AsyncClient(timeout=timeout) as client:
        resp = await client.get(
            f"https://api.covalenthq.com/v1/{chain_id}/address/{treasury_address}/"
            + f"portfolio_v2/?&key=ckey_{getenv('COVALENT_KEY')}"
        )

        data = resp.json()["data"]

    db.hset(CACHE_HASH, cache_key, json.dumps(data))

    return data


async def get_treasury(portfolio: Dict[str, Any]) -> Treasury:

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

    assets = [
        ERC20(
            item["contract_name"],
            item["contract_ticker_symbol"],
            item["contract_address"],
            item["holdings"][0]["close"]["quote"],
        )
        for item in portfolio["items"]
        if item["holdings"][0]["close"]["quote"]
    ]

    return Treasury(portfolio["address"], assets, windows)
