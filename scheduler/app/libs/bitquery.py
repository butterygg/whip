import json
import dateutil
from dataclasses import dataclass
from datetime import datetime
import os
from httpx import AsyncClient
from pytz import UTC

from .. import db


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
class BitqueryTransfer:
    timestamp: datetime
    amount: float  # transfer amount
    value: float  # balance after transfer happened


CACHE_HASH = "bitquery_eth"
CACHE_KEY_TEMPLATE = "{address}_{date}"


async def get_eth_transactions(address: str) -> list[BitqueryTransfer]:
    cache_date = dateutil.utils.today(UTC).strftime("%Y-%m-%d")
    cache_key = CACHE_KEY_TEMPLATE.format(address=address, date=cache_date)
    if db.hexists(CACHE_HASH, cache_key):
        balance_hist_data = json.loads(db.hget(CACHE_HASH, cache_key))

    else:

        async def get_balance_hist_data():
            async with AsyncClient(headers={"X-API-KEY": BITQUERY_API_KEY}) as client:
                resp = await client.post(
                    BITQUERY_URL,
                    json={"query": ETH_QUERY_TEMPLATE.replace("$address", address)},
                )
                resp.raise_for_status()
                return resp.json()["data"]["ethereum"]["address"][0]["balances"][0][
                    "history"
                ]

        balance_hist_data = await get_balance_hist_data()
        db.hset(CACHE_HASH, cache_key, json.dumps(balance_hist_data))

    return [
        BitqueryTransfer(
            dateutil.parser.parse(hist_item["timestamp"]),
            hist_item["transferAmount"],
            hist_item["value"],
        )
        for hist_item in balance_hist_data
    ]
