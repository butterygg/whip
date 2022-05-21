from dateutil import parser
from os import getenv
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from httpx import AsyncClient, Timeout
from ..types import ERC20, Quote, Treasury, HistoricalPrice

load_dotenv


async def get_treasury_portfolio(
    treasury_address: str, chain_id: Optional[int] = 1
) -> Dict[str, Any]:
    timeout = Timeout(10.0, read=15.0, connect=30.0)
    async with AsyncClient(timeout=timeout) as client:
        resp = await client.get(
            f"https://api.covalenthq.com/v1/{chain_id}/address/{treasury_address}/"
            + f"portfolio_v2/?&key=ckey_{getenv('COVALENT_KEY')}"
        )

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
                    Quote(parser.parse(holding["timestamp"]), holding["quote_rate"])
                    for holding in item["holdings"]
                ],
            )
        )

    assets = [
        ERC20(
            item["contract_name"],
            item["contract_ticker_symbol"],
            item["contract_address"],
            item["holdings"][0]["close"]["quote"],
        )
        for item in portfolio["items"]
        if item["holdings"][0]["close"]["quote"]
    ]

    return Treasury(portfolio["address"], assets, windows)
