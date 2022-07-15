import json
from typing import Any, Union

import redis

CHAIN_ID = 1


def store_treasuries_metadata(
    provider: Union[redis.Redis, redis.client.Pipeline],
    addresses: list[Union[str, None]],
    chain_id: int = CHAIN_ID,
):
    payload = [
        json.dumps({"address": address, "chain_id": chain_id}) for address in addresses
    ]
    provider.sadd("treasuries", *payload)


def retrieve_treasuries_metadata(
    provider: Union[redis.Redis, redis.client.Pipeline]
) -> set[tuple[str, int]]:
    treasuries = [
        tuple(json.loads(t).values()) for t in provider.smembers("treasuries")
    ]
    return set(treasuries)


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
