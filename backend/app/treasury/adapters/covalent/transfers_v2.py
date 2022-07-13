import json
from os import getenv
from typing import Any, Generator, Optional

import dateutil
from celery.utils.log import get_logger
from httpx import AsyncClient, HTTPStatusError, Timeout
from pytz import UTC

from .... import db
from ...models import Transfer

CACHE_HASH_TRANSFERS = "covalent_transfers"
CACHE_KEY_TEMPLATE_TRANSFERS = "{treasury_address}_{contract_address}_{chain_id}_{date}"


async def _get_transfers_data(
    treasury_address: str, contract_address: str, chain_id: int
) -> dict[str, Any]:
    async with AsyncClient(timeout=Timeout(10.0, read=60.0, connect=90.0)) as client:
        resp = await client.get(
            f"https://api.covalenthq.com/v1/{chain_id}/address/{treasury_address}"
            + "/transfers_v2/?quote-currency=USD&format=JSON"
            + f"&contract-address={contract_address}&key=ckey_{getenv('COVALENT_KEY')}"
        )
    resp.raise_for_status()
    return resp.json()["data"]


TYPE_SIGN = {"OUT": -1, "IN": 1}


async def get_token_transfers(
    treasury_address: str, contract_address: str, chain_id: Optional[int] = 1
) -> Generator[Transfer, None, None]:
    """Yields Transfer objects without balance, backwards in time

    Notes
    ---
    The historical token balancce of the given treasury is partial
    because, naturaly, covalent's transfers_v2 endpoint only returns
    historical transfers and doesn't return the balance at the time
    of transfer.

    Thus, the balance for a given treasury can only be calculated for
    the date of transfer from the covalent response.
    """
    cache_date = dateutil.utils.today(UTC).strftime("%Y-%m-%d")
    cache_key = CACHE_KEY_TEMPLATE_TRANSFERS.format(
        treasury_address=treasury_address,
        contract_address=contract_address,
        chain_id=chain_id,
        date=cache_date,
    )

    if db.hexists(CACHE_HASH_TRANSFERS, cache_key):
        transfers_data = json.loads(db.hget(CACHE_HASH_TRANSFERS, cache_key))
    else:
        try:
            transfers_data = await _get_transfers_data(
                treasury_address, contract_address, chain_id
            )
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

        db.hset(CACHE_HASH_TRANSFERS, cache_key, json.dumps(transfers_data))

    for block_transaction in transfers_data["items"]:
        block_date = dateutil.parser.parse(block_transaction["block_signed_at"])
        for transfer_item in block_transaction["transfers"]:
            delta = int(transfer_item["delta"])
            decimals = int(transfer_item["contract_decimals"])
            amount = TYPE_SIGN[transfer_item["transfer_type"]] * delta / 10**decimals
            yield Transfer(timestamp=block_date, amount=amount)
