from typing import Union
import redis
import json

from . import db


CHAIN_ID = 1


def store_treasury_metadata(address: str, chain_id: int = CHAIN_ID):
    for _addr, _chain_id in (json.loads(t) for t in db.lrange("treasuries", 0, -1)):
        if (_addr, _chain_id) == (address, chain_id):
            return
    db.rpush("treasuries", json.dumps([address, chain_id]))


def retrieve_treasuries_metadata() -> list[tuple[str, int]]:
    return [tuple(json.loads(t)) for t in db.lrange("treasuries", 0, -1)]


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


def store_asset_hist_performance(
    symbol: str,
    asset_hist_performance_json: str,
    provider: Union[redis.Redis, redis.client.Pipeline] = db,
):
    provider.hset("asset_hist_performance", symbol, asset_hist_performance_json)
