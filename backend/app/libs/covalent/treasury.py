# pylint: disable=duplicate-code
import json
from os import getenv
from typing import Any, Dict, List, Optional

import dateutil
from httpx import AsyncClient, Timeout
from pytz import UTC

from ... import db
from ..types import ERC20, HistoricalPrice, Quote, Treasury

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

    timeout = Timeout(10.0, read=30.0, connect=45.0)
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

    # These tokens don't receive a valid response from covalent's
    # portfolio balances. So we blacklist them
    blacklist = [
        "0x6a113e4caa8aa29c02e535580027a1a3203f43fb",  # mEth
        "0x7cf56db0f7781d478d5a96f6ee8e0b5cbaaf8ad2",  # OMIC / Omicron
        "0x39abe870f44188f66c39eb54eb87ee8f080bf20e",  # Omicron covid
        "0x3301ee63fb29f863f2333bd4466acb46cd8323e6",  # Akita Inu
    ]

    assets = [
        ERC20(
            item["contract_name"],
            item["contract_ticker_symbol"],
            item["contract_address"],
            item["holdings"][0]["close"]["quote"],
        )
        for item in portfolio["items"]
        if item["holdings"][0]["close"]["quote"]
        and item["contract_address"] not in blacklist
        and item["holdings"]
        and item["holdings"][0]["close"]["quote"] < 10**18
    ]

    return Treasury(portfolio["address"], assets, windows)
