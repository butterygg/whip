from httpx import Client, Timeout

from .storage_helpers import store_token_whitelist


def get_coingecko_token_list():
    timeout = Timeout(10.0, read=30.0, connect=15.0)
    with Client(timeout=timeout) as client:
        resp = client.get("https://tokens.coingecko.com/uniswap/all.json")

        tokens = resp.json()["tokens"]
        for token in tokens:
            if token["chainId"] == 1:
                store_token_whitelist(token["address"])
