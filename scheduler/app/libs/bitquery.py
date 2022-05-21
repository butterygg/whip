from dataclasses import dataclass
from datetime import datetime
import os

import requests

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


def get_eth_transactions(address: str) -> list[BitqueryTransfer]:
    headers = {"X-API-KEY": BITQUERY_API_KEY}
    resp = requests.post(
        BITQUERY_URL,
        json={"query": ETH_QUERY_TEMPLATE.replace("$address", address)},
        headers=headers,
    )
    resp.raise_for_status()
    return [
        BitqueryTransfer(
            datetime.strptime(hist_item["timestamp"][:-6], "%Y-%m-%dT%H:%M:%S"),
            hist_item["transferAmount"],
            hist_item["value"],
        )
        for hist_item in resp.json()["data"]["ethereum"]["address"][0]["balances"][0][
            "history"
        ]
    ]
