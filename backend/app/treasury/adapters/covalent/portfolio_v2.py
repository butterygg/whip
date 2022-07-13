# pylint: disable=duplicate-code
import json
from os import getenv
from typing import Any, Optional

import dateutil
from celery.utils.log import get_logger
from httpx import AsyncClient, HTTPStatusError, Timeout
from pytz import UTC

from .... import db
from ...models import ERC20, Treasury

CACHE_HASH_TREASURY = "covalent_treasury"
CACHE_KEY_TEMPLATE_PORTFOLIO = "{address}_{chain_id}_{date}"


async def _get_portfolio_data(
    treasury_address: str, chain_id: Optional[int] = 1
) -> dict[str, Any]:
    timeout = Timeout(10.0, read=60.0, connect=90.0)
    async with AsyncClient(timeout=timeout) as client:
        url = (
            f"https://api.covalenthq.com/v1/{chain_id}/address/{treasury_address}/"
            + f"portfolio_v2/?&key=ckey_{getenv('COVALENT_KEY')}"
        )
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()["data"]

    return data


async def get_treasury(
    treasury_address: str, whitelist: list[str], chain_id: Optional[int] = 1
) -> Treasury:
    cache_date = dateutil.utils.today(UTC).strftime("%Y-%m-%d")
    cache_key = CACHE_KEY_TEMPLATE_PORTFOLIO.format(
        address=treasury_address, chain_id=chain_id, date=cache_date
    )

    if db.hexists(CACHE_HASH_TREASURY, cache_key):
        portfolio_data = json.loads(db.hget(CACHE_HASH_TREASURY, cache_key))
    else:
        try:
            portfolio_data = await _get_portfolio_data(treasury_address, chain_id)
        except (
            HTTPStatusError,
            json.decoder.JSONDecodeError,
            KeyError,
        ) as error:
            logger = get_logger(__name__)
            if error.__class__ is HTTPStatusError:
                logger.error(
                    "unable to receive a Covalent `portfolio_v2` API response",
                    exc_info=error,
                )
            logger.error(
                "error processing Covalent `portfolio_v2` API response", exc_info=error
            )
            raise

        db.hset(CACHE_HASH_TREASURY, cache_key, json.dumps(portfolio_data))

    # Certain tokens a treasury may hold are noted as spam.
    # To prevent these tokens from corrupting the data,
    # we filter them out via a whitelist provided by tokenlists.org
    assets = [
        ERC20(
            token_name=item["contract_name"],
            token_symbol=item["contract_ticker_symbol"],
            token_address=item["contract_address"],
            balance_usd=item["holdings"][0]["close"]["quote"],
            balance=int(item["holdings"][0]["close"]["balance"])
            / 10 ** int(item["contract_decimals"]),
        )
        for item in portfolio_data["items"]
        if item["holdings"][0]["close"]["quote"]
        and item["contract_address"] in whitelist
        and item["holdings"]
    ]

    return Treasury(portfolio_data["address"], assets)
