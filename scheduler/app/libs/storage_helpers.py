from typing import Union
import redis
import ujson

from . import db


CHAIN_ID = 1


def store_treasury_metadata(address: str):
    stored_addresses = [
        ujson.loads(t)["address"] for t in db.lrange("treasuries", 0, -1)
    ]
    if address in stored_addresses:
        return
    db.rpush({"address": address, "chain_id": CHAIN_ID})


def retrieve_treasuries_metadata() -> list[tuple[str, int]]:
    treasuries_meta = [ujson.loads(t) for t in db.lrange("treasuries", 0, -1)]
    return [(tm["address"], tm.get("chain_id", CHAIN_ID)) for tm in treasuries_meta]


BALANCES_KEY_TEMPLATE = "{address}_{symbol}"


def store_asset_hist_balance(
    treasury_address: str,
    symbol: str,
    asset_hist_balance_json: str,
    provider: Union[redis.Redis, redis.client.Pipeline] = db,
):
    provider.hset(
        "balances",
        BALANCES_KEY_TEMPLATE.format(address=treasury_address, symbol=symbol),
        asset_hist_balance_json,
    )
