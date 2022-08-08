import json
import os
from typing import Any, Generator, Optional

import dateutil
from celery.utils.log import get_logger
from httpx import AsyncClient, HTTPStatusError, Timeout

from .... import db
from ...models import Transfer
from .. import set_data_and_expiry

CACHE_KEY_TEMPLATE_TRANSFERS = (
    "covalent_transfer_items_{treasury_address}_{contract_address}_{chain_id}_{date}"
)

KEY = os.getenv("COVALENT_KEY")
TRANSFERS_V2_URL_TEMPLATE = (
    "https://api.covalenthq.com/v1/{chain_id}/address/{treasury_address}/transfers_v2/"
)


async def _get_transfer_items(
    treasury_address: str, contract_address: str, chain_id: int
) -> Generator[dict[str, Any], None, None]:
    page_number = 0
    while True:
        async with AsyncClient(
            timeout=Timeout(10.0, read=60.0, connect=90.0)
        ) as client:
            resp = await client.get(
                TRANSFERS_V2_URL_TEMPLATE.format(
                    chain_id=chain_id, treasury_address=treasury_address
                ),
                params={
                    "quote-currency": "USD",
                    "format": "JSON",
                    "contract-address": contract_address,
                    "key": f"ckey_{KEY}",
                    "page-number": page_number,
                },
            )
        resp.raise_for_status()
        data = resp.json()["data"]
        for item in data["items"]:
            yield item
        if not data["pagination"]["has_more"]:
            break
        page_number += 1


TYPE_SIGN = {"OUT": -1, "IN": 1}


def _transfers_of_items(transfer_items: list[dict[str, Any]]):
    for block_transaction in transfer_items:
        block_date = dateutil.parser.parse(block_transaction["block_signed_at"])
        for transfer in block_transaction["transfers"]:
            delta = int(transfer["delta"])
            decimals = int(transfer["contract_decimals"])
            if decimals < 0:
                logger = get_logger(__name__)
                logger.error(
                    "Covalent returned negative decimals on contract %s %s %s",
                    transfer["contract_name"],
                    transfer["contract_ticker_symbol"],
                    transfer["contract_address"],
                )
            amount = TYPE_SIGN[transfer["transfer_type"]] * delta / 10**decimals
            yield Transfer(timestamp=block_date, amount=amount)


async def get_token_transfers(
    treasury_address: str, contract_address: str, chain_id: Optional[int] = 1
) -> list[Transfer]:
    """Returns a list of Transfer objects without balance, backwards in time

    Notes
    ---
    The historical token balancce of the given treasury is partial
    because, naturaly, covalent's transfers_v2 endpoint only returns
    historical transfers and doesn't return the balance at the time
    of transfer.

    Thus, the balance for a given treasury can only be calculated for
    the date of transfer from the covalent response.
    """
    cache_date = dateutil.utils.today(dateutil.tz.UTC).strftime("%Y-%m-%d")
    cache_key = CACHE_KEY_TEMPLATE_TRANSFERS.format(
        treasury_address=treasury_address,
        contract_address=contract_address,
        chain_id=chain_id,
        date=cache_date,
    )

    if db.exists(cache_key) > 0:
        transfer_items = json.loads(db.get(cache_key))
    else:
        try:
            transfer_items = [
                _
                async for _ in _get_transfer_items(
                    treasury_address, contract_address, chain_id
                )
            ]
        except (
            HTTPStatusError,
            json.decoder.JSONDecodeError,
            KeyError,
        ) as error:
            logger = get_logger(__name__)
            if error.__class__ is HTTPStatusError:
                logger.error(
                    "unable to receive a Covalent `transfers_v2` API response",
                    exc_info=error,
                )
            logger.error(
                "error processing Covalent `transfers_v2` API response", exc_info=error
            )
            raise

        set_data_and_expiry(cache_key, json.dumps(transfer_items), db)

    return list(_transfers_of_items(transfer_items))
