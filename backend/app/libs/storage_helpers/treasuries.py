from httpx import Client, Timeout
import redis

from .storage_helpers import store_treasury_metadata


def cache_treasury_list(provider: redis.Redis):
    timeout = Timeout(10.0, read=30.0, connect=15.0)
    with Client(timeout=timeout) as client:
        resp = client.get(
            "https://api.cryptostats.community/api/v1/treasuries/currentTreasuryPortfolio"
        )
        treasury_portfolios = resp.json()["data"]
    whitelist = ["bitdao", "gitcoin", "uniswap"]
    with provider.pipeline() as pipe:
        for treasury in treasury_portfolios:
            if treasury["id"] in whitelist:
                for address in treasury["metadata"]["treasuries"]:
                    store_treasury_metadata(provider, address)

        pipe.execute(raise_on_error=False)
