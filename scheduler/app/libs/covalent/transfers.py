from os import getenv

from typing import Any, Dict, Optional
from httpx import AsyncClient, Timeout

async def get_token_transfers_for_wallet(treasury_address: str, contract_address: str, chain_id: Optional[int] = 1) -> Dict[str, Any]:
    timeout = Timeout(10.0, read=15.0, connect=30.0)
    async with AsyncClient(timeout=timeout) as client:
        resp = await client.get(
            f"https://api.covalenthq.com/v1/{chain_id}/address/{treasury_address}" +\
                f"/transfers_v2/?quote-currency=USD&format=JSON" +\
                f"&contract-address={contract_address}&key=ckey_{getenv('COVALENT_KEY')}"
        )
    return resp.json()["data"]