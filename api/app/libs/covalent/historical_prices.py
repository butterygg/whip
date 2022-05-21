from os import getenv
from typing import Any, Dict, List, Optional

from httpx import AsyncClient


async def get_historical_price_by_symbol(
    token_symbol: str,
    start_date: str,
    quote: Optional[str] = "USD",
    chain_id: Optional[int] = 1,
) -> Dict[str, Any]:
    if start_date == "a_year_ago":
        from datetime import timedelta
        from dateutil.utils import today
        from dateutil.tz import UTC

        end_date = today(UTC)
        start_date = end_date - timedelta(days=365)
        start_date = start_date.strftime("%Y-%m-%d")

    async with AsyncClient() as client:
        # api.covalenthq.com/v1/pricing/historical/USD/UNI/?quote-currency=USD&format=JSON&from=2021-05-10&key=ckey_30f56650f3a544fe8803d522cb0
        resp = await client.get(
            f"https://api.covalenthq.com/v1/pricing/historical/"
            + f"{quote}/{token_symbol}/?key=ckey_{getenv('COVALENT_KEY')}"
            + f"&quote-currency={quote}"
            + f"&format=JSON"
            + f"&from={start_date}"
        )

        return resp.json()["data"]


async def get_historical_price_by_address(
    token_contract: str,
    start_date: str,
    quote: Optional[str] = "USD",
    chain_id: Optional[int] = 1,
) -> Dict[str, Any]:
    async with AsyncClient() as client:
        resp = await client.get(
            f"https://api.covalenthq.com/v1/pricing/historical_by_addresses_v2/{chain_id}/"
            + f"{quote}/?&key=ckey_{getenv('COVALENT_KEY')}"
            + f"&contract_addresses={token_contract}"
            + f"&from={start_date}/"
        )

        return resp.json()["data"]
