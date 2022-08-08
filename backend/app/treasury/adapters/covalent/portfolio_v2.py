import json
from os import getenv
from typing import Any, Optional

import dateutil
from celery.utils.log import get_logger
from httpx import AsyncClient, HTTPStatusError, Timeout

from .... import db
from ...models import ERC20, Treasury
from .. import set_data_and_expiry

CACHE_KEY_TEMPLATE_PORTFOLIO = "covalent_treasury_{address}_{chain_id}_{date}"


async def _get_portfolio_data(
    treasury_address: str, chain_id: Optional[int] = 1
) -> dict[str, Any]:
    timeout = Timeout(10.0, read=90.0, connect=120.0)
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
    cache_date = dateutil.utils.today(dateutil.tz.UTC).strftime("%Y-%m-%d")
    cache_key = CACHE_KEY_TEMPLATE_PORTFOLIO.format(
        address=treasury_address, chain_id=chain_id, date=cache_date
    )

    if db.exists(cache_key) > 0:
        portfolio_data = json.loads(db.get(cache_key))
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
                    "unable to receive a Covalent `portfolio_v2` API response for %s",
                    treasury_address,
                    exc_info=error,
                )
            logger.error(
                "error processing Covalent `portfolio_v2` API response for %s",
                treasury_address,
                exc_info=error,
            )
            raise

        set_data_and_expiry(cache_key, json.dumps(portfolio_data), db)

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
