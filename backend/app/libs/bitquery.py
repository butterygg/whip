import json
import os
from dataclasses import dataclass
from typing import Any

import dateutil
from httpx import AsyncClient, Timeout
from pytz import UTC

from .. import db
from ..treasury.adapters.types import Transfer

BITQUERY_API_KEY = os.environ["BITQUERY_API_KEY"]
ETH_QUERY_TEMPLATE = """
query{
  ethereum{
    address(address: {is: "$address"}){
      balances(currency: {is: "ETH"}, date: {till: "2022-05-01"}){
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


@dataclass
class BitqueryTransfer(Transfer):
    amount: float  # transfer amount


CACHE_HASH = "bitquery_eth"
CACHE_KEY_TEMPLATE = "{address}_{date}"


async def _get_data(treasury_address: str) -> Any:
    timeout = Timeout(10.0, read=15.0, connect=30.0)
    async with AsyncClient(
        headers={"X-API-KEY": BITQUERY_API_KEY}, timeout=timeout
    ) as client:
        resp = await client.post(
            BITQUERY_URL,
            json={"query": ETH_QUERY_TEMPLATE.replace("$address", treasury_address)},
        )
        resp.raise_for_status()
        try:
            data = resp.json()["data"]
            return data["ethereum"]["address"][0]["balances"][0]["history"]
        except TypeError:
            return []


async def get_eth_transfers(treasury_address: str) -> list[BitqueryTransfer]:
    cache_date = dateutil.utils.today(UTC).strftime("%Y-%m-%d")
    cache_key = CACHE_KEY_TEMPLATE.format(address=treasury_address, date=cache_date)
    if db.hexists(CACHE_HASH, cache_key):
        balance_hist_data = json.loads(db.hget(CACHE_HASH, cache_key))

    else:
        balance_hist_data = await _get_data(treasury_address)
        db.hset(CACHE_HASH, cache_key, json.dumps(balance_hist_data))

    return [
        BitqueryTransfer(
            timestamp=dateutil.parser.parse(hist_item["timestamp"]),
            balance=hist_item["value"],
            amount=hist_item["transferAmount"],
        )
        for hist_item in balance_hist_data
    ]
