import redis
from httpx import Client, Timeout

from .storage_helpers import store_treasury_metadata


def cache_treasury_list(provider: redis.Redis):
    timeout = Timeout(10.0, read=30.0, connect=15.0)
    with Client(timeout=timeout) as client:
        resp = client.get(
            "https://api.cryptostats.community/api/v1/treasuries/currentTreasuryPortfolio"
        )
        treasury_portfolios = resp.json()["data"]
    for treasury in treasury_portfolios:
        treasuries = []
        for address in treasury["metadata"]["treasuries"]:
            treasuries.append(address)
        if treasuries:
            store_treasury_metadata(provider, treasuries)
