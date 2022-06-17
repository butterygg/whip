import json
from typing import Any, Union

import redis

from .. import db

CHAIN_ID = 1


def store_treasury_metadata(address: str, chain_id: int = CHAIN_ID):
    for _addr, _chain_id in (json.loads(t) for t in db.lrange("treasuries", 0, -1)):
        if (_addr, _chain_id) == (address, chain_id):
            return
    db.rpush("treasuries", json.dumps([address, chain_id]))


def retrieve_treasuries_metadata() -> list[tuple[str, int]]:
    return [tuple(json.loads(t).values()) for t in db.lrange("treasuries", 0, -1)]


def store_token_whitelist(address: str):
    for _addr in db.lrange("whitelist", 0, -1):
        if _addr == address:
            return
    db.rpush("whitelist", address)


def retrieve_token_whitelist() -> list[str]:
    return db.lrange("whitelist", 0, -1)


BALANCES_KEY_TEMPLATE = "{address}_{symbol}"


def store_hash_set(
    _hash: str,
    key: str,
    value: Any,
    provider: Union[redis.Redis, redis.client.Pipeline] = db,
):
    provider.hset(_hash, key, value)


def store_asset_hist_balance(
    treasury_address: str,
    symbol: str,
    asset_hist_balance_json: str,
    provider: Union[redis.Redis, redis.client.Pipeline] = db,
):
    store_hash_set(
        "balances",
        BALANCES_KEY_TEMPLATE.format(address=treasury_address, symbol=symbol),
        asset_hist_balance_json,
        provider,
    )


def store_asset_hist_performance(
    symbol: str,
    asset_hist_performance_json: str,
    provider: Union[redis.Redis, redis.client.Pipeline] = db,
):
    store_hash_set(
        "asset_hist_performance", symbol, asset_hist_performance_json, provider
    )


def store_asset_correlations(
    address: str,
    asset_correlations_json: str,
    provider: Union[redis.Redis, redis.client.Pipeline] = db,
):
    store_hash_set("asset_correlations", address, asset_correlations_json, provider)
