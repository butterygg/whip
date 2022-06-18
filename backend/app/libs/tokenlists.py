from asyncio import gather

from httpx import AsyncClient, Timeout

from .storage_helpers import retrieve_token_whitelist, store_token_whitelist


async def get_token_list(token_list: str):
    timeout = Timeout(10.0, read=30.0, connect=15.0)
    async with AsyncClient(timeout=timeout) as client:
        resp = await client.get(token_list)

        whitelist = [
            token["address"] for token in resp.json()["tokens"] if token["chainId"] == 1
        ]
        store_token_whitelist(whitelist)


async def get_coingecko_token_list():
    await get_token_list("https://tokens.coingecko.com/uniswap/all.json")


async def get_cmc_token_list():
    await get_token_list("https://api.coinmarketcap.com/data-api/v3/uniswap/all.json")


async def get_all_token_lists():
    await gather(get_coingecko_token_list(), get_cmc_token_list())


async def maybe_populate_whitelist() -> list[str]:
    token_whitelist = retrieve_token_whitelist()
    if not token_whitelist:
        await get_all_token_lists()
        token_whitelist = retrieve_token_whitelist()
    return token_whitelist
