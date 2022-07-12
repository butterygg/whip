import json
from dataclasses import dataclass
from os import getenv
from typing import Any, Generator, Optional

import dateutil
from celery.utils.log import get_logger
from httpx import AsyncClient, HTTPStatusError, Timeout
from pytz import UTC

from .... import db
from ....libs.types import Transfer

CACHE_HASH_TRANSFERS = "covalent_transfers"
CACHE_KEY_TEMPLATE_TRANSFERS = "{treasury_address}_{contract_address}_{chain_id}_{date}"


@dataclass
class CovalentTransfer(Transfer):
    pass


async def _get_transfers_data(
    treasury_address: str, contract_address: str, chain_id: int
) -> dict[str, Any]:
    async with AsyncClient(timeout=Timeout(10.0, read=15.0, connect=30.0)) as client:
        resp = await client.get(
            f"https://api.covalenthq.com/v1/{chain_id}/address/{treasury_address}"
            + "/transfers_v2/?quote-currency=USD&format=JSON"
            + f"&contract-address={contract_address}&key=ckey_{getenv('COVALENT_KEY')}"
        )
    resp.raise_for_status()
    return resp.json()["data"]


def _gen_transfers(
    asset_trans_history: dict[str, Any]
) -> Generator[CovalentTransfer, None, None]:
    """Yields CovalentTransfers of a given treasury's *partial*, historical token
    balance.

    Parameters
    ---
    asset_trans_history: Dict[str, Any]
        A covalent response from their `transfers_v2` endpoint.
    start: str
        Date to query transfers from. This as well as `end` should be
        formatted as `%Y-%m-%d`
    end: str
        Date to end transfer query

    Notes
    ---
    The historical token balancce of the given treasury is partial
    because, naturaly, covalent's transfers_v2 endpoint only returns
    historical transfers and doesn't return the balance at the time
    of transfer.

    Thus, the balance for a given treasury can only be calculated for
    the date of transfer from the covalent response.

    ---

    The end date allows the historical query to end, returning the
    historical balance from between the start and end dates.
    """
    blocks = asset_trans_history["items"]
    curr_balance = 0.0
    end_index = len(blocks) - 1
    for i in range(end_index, -1, -1):
        transfers = blocks[i]["transfers"]
        decimals = int(transfers[0]["contract_decimals"])

        for transfer in transfers:
            block_date = dateutil.parser.parse(transfer["block_signed_at"])

            delta = int(transfer["delta"])
            if transfer["transfer_type"] == "IN":
                curr_balance += delta / 10**decimals if decimals > 0 else 1
                yield CovalentTransfer(balance=curr_balance, timestamp=block_date)
            else:
                curr_balance -= delta / 10**decimals if decimals > 0 else 1
                yield CovalentTransfer(balance=curr_balance, timestamp=block_date)


async def get_token_transfers(
    treasury_address: str, contract_address: str, chain_id: Optional[int] = 1
) -> Optional[list[CovalentTransfer]]:
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

        if transfers_data:
            db.hset(CACHE_HASH_TRANSFERS, cache_key, json.dumps(transfers_data))

    if not transfers_data:
        return None

    return list(_gen_transfers(transfers_data))
