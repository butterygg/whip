import json
from typing import Any, Union

import redis

CHAIN_ID = 1


def store_treasury_metadata(
    provider: Union[redis.Redis, redis.client.Pipeline],
    address: str,
    chain_id: int = CHAIN_ID,
):
    if provider.hexists("treasuries", address):
        return
    provider.hset("treasuries", address, json.dumps({"chain_id": chain_id}))


def retrieve_treasuries_metadata(
    provider: Union[redis.Redis, redis.client.Pipeline]
) -> list[tuple[str, int]]:
    blacklist = [
        "0x283Af0B28c62C092C9727F1Ee09c02CA627EB7F5",
        "0x4441776e6a5d61fa024a5117bfc26b953ad1f425",
        "0x4750c43867ef5f89869132eccf19b9b6c4286e1a",
        "0x4b4e140d1f131fdad6fb59c13af796fd194e4135",
        "0x3d30b1ab88d487b0f3061f40de76845bec3f1e94",
    ]
    return [
        (address, json.loads(value)["chain_id"])
        for address, value in provider.hgetall("treasuries").items()
        if address not in blacklist
    ]


def store_token_whitelist(
    address: list[str], provider: Union[redis.Redis, redis.client.Pipeline]
):
    provider.sadd("whitelist", *address)


def retrieve_token_whitelist(
    provider: Union[redis.Redis, redis.client.Pipeline]
) -> list[str]:
    return provider.smembers("whitelist")


BALANCES_KEY_TEMPLATE = "{address}_{symbol}"


def store_hash_set(
    _hash: str,
    key: str,
    value: Any,
    provider: Union[redis.Redis, redis.client.Pipeline],
):
    provider.hset(_hash, key, value)


def store_asset_hist_balance(
    treasury_address: str,
    symbol: str,
    asset_hist_balance_json: str,
    provider: Union[redis.Redis, redis.client.Pipeline],
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
    provider: Union[redis.Redis, redis.client.Pipeline],
):
    store_hash_set(
        "asset_hist_performance", symbol, asset_hist_performance_json, provider
    )


def store_asset_correlations(
    address: str,
    asset_correlations_json: str,
    provider: Union[redis.Redis, redis.client.Pipeline],
):
    store_hash_set("asset_correlations", address, asset_correlations_json, provider)
