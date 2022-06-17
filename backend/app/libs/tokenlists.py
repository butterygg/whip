from asyncio import gather
from httpx import AsyncClient, Timeout

from .storage_helpers import store_token_whitelist


async def get_token_list(token_list: str):
    timeout = Timeout(10.0, read=30.0, connect=15.0)
    async with AsyncClient(timeout=timeout) as client:
        resp = await client.get(token_list)

        tokens = resp.json()["tokens"]
        for token in tokens:
            if token["chainId"] == 1:
                store_token_whitelist(token["address"])


async def get_coingecko_token_list():
    await get_token_list("https://tokens.coingecko.com/uniswap/all.json")


async def get_cmc_token_list():
    await get_token_list("https://api.coinmarketcap.com/data-api/v3/uniswap/all.json")


async def get_all_token_lists():
    await gather(get_coingecko_token_list(), get_cmc_token_list())
