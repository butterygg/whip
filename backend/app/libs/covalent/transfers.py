# pylint: disable=duplicate-code
import json
from dataclasses import dataclass
from os import getenv
from typing import Any, Generator, Optional

import dateutil
from dateutil import parser
from httpx import AsyncClient, Timeout
from pytz import UTC

from ... import db
from ..types import Transfer


@dataclass
class CovalentTransfer(Transfer):
    pass


CACHE_HASH = "covalent_transfers"
CACHE_KEY_TEMPLATE = "{treasury_address}_{contract_address}_{chain_id}_{date}"


async def _get_data(treasury_address: str, contract_address: str, chain_id: int) -> Any:
    async with AsyncClient(timeout=Timeout(10.0, read=15.0, connect=30.0)) as client:
        resp = await client.get(
            f"https://api.covalenthq.com/v1/{chain_id}/address/{treasury_address}"
            + "/transfers_v2/?quote-currency=USD&format=JSON"
            + f"&contract-address={contract_address}&key=ckey_{getenv('COVALENT_KEY')}"
        )
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
            block_date = parser.parse(transfer["block_signed_at"])

            if not transfer["quote_rate"]:
                continue
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
    cache_key = CACHE_KEY_TEMPLATE.format(
        treasury_address=treasury_address,
        contract_address=contract_address,
        chain_id=chain_id,
        date=cache_date,
    )

    if db.hexists(CACHE_HASH, cache_key):
        balance_hist_data = json.loads(db.hget(CACHE_HASH, cache_key))
    else:
        balance_hist_data = await _get_data(
            treasury_address, contract_address, chain_id
        )
        db.hset(CACHE_HASH, cache_key, json.dumps(balance_hist_data))

    if not balance_hist_data:
        return None

    return list(_gen_transfers(balance_hist_data))
