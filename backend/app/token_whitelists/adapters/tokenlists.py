from typing import Any

from httpx import AsyncClient, Timeout

from .utils import get_whitelists_from_apis


async def get_raw_tokenlist(tokenlist_url: str) -> list[dict[str, Any]]:
    timeout = Timeout(10.0, read=30.0, connect=15.0)
    async with AsyncClient(timeout=timeout) as client:
        resp = await client.get(tokenlist_url)
        resp.raise_for_status()
        return resp.json()["tokens"]


def process_raw_tokenlist(raw_tokenlist: list[dict[str, Any]]):
    tokenlist_whitelist = [
        token["address"] for token in raw_tokenlist if token["chainId"] == 1
    ]

    tokenlist_whitelist.append("0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
    return tokenlist_whitelist


async def get_processed_tokenlists(tokenlist_url: str) -> list[str]:
    raw_tokenlist = await get_raw_tokenlist(tokenlist_url)
    processed_tokenlist_whitelist = process_raw_tokenlist(raw_tokenlist)

    return processed_tokenlist_whitelist


async def get_uniswap_pairs_tokenlists() -> tuple[str, list[str]]:
    path = "jab416171/uniswap-pairtokens/master/uniswap_pair_tokens.json"
    datasource = f"https://raw.githubusercontent.com/{path}"
    return (datasource, await get_processed_tokenlists(datasource))


async def get_coingecko_tokenlists() -> tuple[str, list[str]]:
    datasource = "https://tokens.coingecko.com/uniswap/all.json"
    return (datasource, await get_processed_tokenlists(datasource))


async def get_cmc_tokenlists() -> tuple[str, list[str]]:
    datasource = "https://api.coinmarketcap.com/data-api/v3/uniswap/all.json"
    return (datasource, await get_processed_tokenlists(datasource))


async def get_all_tokenlists() -> list[str]:
    return await get_whitelists_from_apis(
        [
            get_cmc_tokenlists,
            get_coingecko_tokenlists,
            get_uniswap_pairs_tokenlists,
        ]
    )
