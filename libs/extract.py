from os import getenv
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from httpx import AsyncClient
from .types import Treasury, ERC20

load_dotenv

async def get_treasury_assets(treasury_address: str, chain_id: Optional[int] = 1) -> Treasury:
    async with AsyncClient() as client:
        resp = await client.get(
            f"https://api.covalenthq.com/v1/{chain_id}/address/{treasury_address}/" +\
                f"portfolio_v2/?&key=ckey_{getenv('COVALENT_KEY')}")

        resp_json = resp.json()["data"]

        return Treasury(
            treasury_address,
            [ 
                ERC20(
                    item["contract_name"],
                    item["contract_ticker_symbol"],
                    item["contract_address"],
                    int(item["holdings"][0]["close"]["balance"]) 
                        / 10 ** item["contract_decimals"] if item["contract_decimals"] != 0
                        else item["holdings"][0]["close"]["balance"]
                ).__dict__
                for item in resp_json["items"]
            ]
        )
