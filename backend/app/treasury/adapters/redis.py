import json
from datetime import datetime, timedelta
from typing import Union

import redis
from dateutil.tz import UTC

CHAIN_ID = 1


def store_treasuries_metadata(
    provider: Union[redis.Redis, redis.client.Pipeline],
    addresses: list[Union[str, None]],
    chain_id: int = CHAIN_ID,
):
    payload = [json.dumps((address, chain_id)) for address in addresses]
    provider.sadd("treasuries", *payload)


def remove_treasuries_metadata(
    provider: Union[redis.Redis, redis.client.Pipeline],
):
    provider.delete("treasuries")


def retrieve_treasuries_metadata(
    provider: Union[redis.Redis, redis.client.Pipeline]
) -> set[tuple[str, int]]:
    treasuries = [tuple(json.loads(t)) for t in provider.smembers("treasuries")]
    return set(treasuries)


def retrieve_hist_prices(
    symbol: str, provider: Union[redis.Redis, redis.client.Pipeline]
):
    provider.hget("asset_hist_performance", symbol)


def set_data_and_expiry(
    cache_key: str,
    data_to_set: str,
    provider: Union[redis.Redis, redis.client.Pipeline],
):
    provider.set(cache_key, data_to_set)
    if provider.ttl(cache_key) <= 0:
        time_to_evict = datetime.now(tz=UTC) + timedelta(days=1)
        time_to_evict_ts = time_to_evict.replace(
            hour=0, minute=0, second=0, microsecond=0
        ).timestamp()

    provider.expireat(cache_key, int(time_to_evict_ts))
