import json
from os import getenv
from typing import Any, Dict, Optional

import dateutil
from httpx import AsyncClient, Timeout
from pytz import UTC

from .. import db

CACHE_HASH = "covalent_transfers"
CACHE_KEY_TEMPLATE = "{treasury_address}_{contract_address}_{chain_id}_{date}"


async def get_token_transfers_for_wallet(
    treasury_address: str, contract_address: str, chain_id: Optional[int] = 1
) -> Dict[str, Any]:
    cache_date = dateutil.utils.today(UTC).strftime("%Y-%m-%d")
    cache_key = CACHE_KEY_TEMPLATE.format(
        treasury_address=treasury_address,
        contract_address=contract_address,
        chain_id=chain_id,
        date=cache_date,
    )

    if db.hexists(CACHE_HASH, cache_key):
        return json.loads(db.hget(CACHE_HASH, cache_key))

    timeout = Timeout(10.0, read=15.0, connect=30.0)
    async with AsyncClient(timeout=timeout) as client:
        resp = await client.get(
            f"https://api.covalenthq.com/v1/{chain_id}/address/{treasury_address}"
            + f"/transfers_v2/?quote-currency=USD&format=JSON"
            + f"&contract-address={contract_address}&key=ckey_{getenv('COVALENT_KEY')}"
        )
    data = resp.json()["data"]

    db.hset(CACHE_HASH, cache_key, json.dumps(data))

    return data
