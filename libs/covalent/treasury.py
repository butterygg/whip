from dateutil import parser
from os import getenv
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from httpx import AsyncClient
from ..types import ERC20, Quote, Treasury, HistoricalPrice

load_dotenv

async def get_treasury_portfolio(treasury_address: str, chain_id: Optional[int] = 1) -> Dict[str, Any]:
    async with AsyncClient() as client:
        resp = await client.get(
            f"https://api.covalenthq.com/v1/{chain_id}/address/{treasury_address}/" +\
                f"portfolio_v2/?&key=ckey_{getenv('COVALENT_KEY')}")

        return resp.json()["data"]

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
                        parser.parse(holding["timestamp"]),
                        holding["quote_rate"]
                    )
                    for holding in item["holdings"]
                ]
            )
        )

    treasury = Treasury(portfolio["address"], [], windows)
    for item in portfolio["items"]:
        if not item["holdings"][0]["close"]["quote"]:
            continue
        treasury.assets.append(
            ERC20(
                item["contract_name"],
                item["contract_ticker_symbol"],
                item["contract_address"],
                item["holdings"][0]["close"]["quote"]
            ).__dict__
        )

    return treasury
