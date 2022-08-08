import json
import os
from typing import Any

import dateutil
from httpx import AsyncClient, Timeout
from pytz import UTC

from ... import db
from ..models import Transfer
from .redis import set_data_and_expiry

BITQUERY_API_KEY = os.environ["BITQUERY_API_KEY"]
ETH_QUERY_TEMPLATE = """
query{
  ethereum{
    address(address: {is: "$address"}){
      balances(currency: {is: "ETH"}, date: {till: "$end_date"}){
        history{
          transferAmount
          value
          timestamp
        }
      }
    }
  }
}
"""
BITQUERY_URL = "https://graphql.bitquery.io/"


CACHE_KEY_TEMPLATE = "bitquery_eth_{address}_{date}"


async def _get_data(treasury_address: str, end_date: str) -> Any:
    timeout = Timeout(10.0, read=15.0, connect=30.0)
    query_body = ETH_QUERY_TEMPLATE.replace("$address", treasury_address)
    async with AsyncClient(
        headers={"X-API-KEY": BITQUERY_API_KEY}, timeout=timeout
    ) as client:
        resp = await client.post(
            BITQUERY_URL,
            json={"query": query_body.replace("$end_date", end_date)},
        )
        resp.raise_for_status()
        try:
            data = resp.json()["data"]
            return data["ethereum"]["address"][0]["balances"][0]["history"]
        except TypeError:
            return []


async def get_eth_transfers(treasury_address: str) -> list[Transfer]:
    cache_date: str = dateutil.utils.today(UTC).strftime("%Y-%m-%d")
    cache_key = CACHE_KEY_TEMPLATE.format(address=treasury_address, date=cache_date)
    if db.exists(cache_key) > 0:
        balance_hist_data = json.loads(db.get(cache_key))
    else:
        balance_hist_data = await _get_data(treasury_address, cache_date)
        set_data_and_expiry(cache_key, json.dumps(balance_hist_data), db)

    return [
        Transfer(
            timestamp=dateutil.parser.parse(hist_item["timestamp"]),
            amount=hist_item["transferAmount"],
        )
        for hist_item in balance_hist_data
    ]
