import json
from datetime import datetime, timedelta
from typing import Any, Union

import redis
from dateutil.tz import UTC

BALANCES_KEY_TEMPLATE = "{address}_{symbol}"


def store_troublesome_treasuries(
    troublesome_treasuries: set[tuple[str, int]],
    provider: Union[redis.Redis, redis.client.Pipeline],
):
    troublesome_treasury_payload = {
        json.dumps(troublesome_treasury)
        for troublesome_treasury in troublesome_treasuries
    }

    provider.sadd("treasuries_to_retry", *troublesome_treasury_payload)


def retrieve_troublesome_treasuries(
    provider: Union[redis.Redis, redis.client.Pipeline]
) -> set[tuple[str, int]]:
    troublesome_treasuries: set[tuple[str, int]] = {
        tuple(json.loads(t)) for t in provider.smembers("treasuries_to_retry")
    }
    return troublesome_treasuries


def store_hash_set(
    _hash: str,
    key: str,
    value: Any,
    provider: Union[redis.Redis, redis.client.Pipeline],
):
    provider.hset(_hash, key, value)

    time_to_evict = datetime.now(tz=UTC) + timedelta(days=1)
    provider.expireat(
        _hash,
        time_to_evict.replace(hour=0, minute=0, second=0),
    )


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
