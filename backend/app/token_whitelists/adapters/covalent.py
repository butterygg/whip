import os
from typing import Any, Generator

from httpx import AsyncClient, Timeout

from .utils import get_whitelists_from_apis

COVALENT_KEY = os.getenv("COVALENT_KEY")
COVALENT_POOLS_URL = "https://api.covalenthq.com/v1/{chain_id}/xy=k/{protocol}/pools/"


async def get_covalent_pairs(
    client: AsyncClient, url_options: dict[str, Any]
) -> dict[str, Any]:
    async with client:
        resp = await client.get(
            COVALENT_POOLS_URL.format(
                chain_id=url_options["chain_id"], protocol=url_options["protocol"]
            ),
            params={
                "quote-currency": "USD",
                "format": "JSON",
                "page-number": url_options["page_number"],
                "page-size": 250,
                "key": f"ckey_{COVALENT_KEY}",
            },
        )
        resp.raise_for_status()
        return resp.json()["data"]


async def covalent_pairs_generator(
    protocol: str, chain_id=1
) -> Generator[dict[str, Any], None, None]:
    page_number = 0
    while True:
        data = await get_covalent_pairs(
            AsyncClient(timeout=Timeout(10.0, read=60.0, connect=90.0)),
            {"chain_id": chain_id, "protocol": protocol, "page_number": page_number},
        )
        for item in data["items"]:
            yield item
        if not data["pagination"]["has_more"]:
            break
        page_number += 1


async def get_covalent_pair_list(protocol: str, chain_id=1) -> list[str]:
    whitelist = [
        item["exchange"] async for item in covalent_pairs_generator(protocol, chain_id)
    ]
    return whitelist


async def get_uniswap_v2_pairs_covalent() -> tuple[str, list[str]]:
    datasource = COVALENT_POOLS_URL.format(chain_id=1, protocol="uniswap_v2")
    return (datasource, await get_covalent_pair_list("uniswap_v2"))


async def get_sushiswap_pairs_covalent() -> tuple[str, list[str]]:
    datasource = COVALENT_POOLS_URL.format(chain_id=1, protocol="sushiswap")
    return (datasource, await get_covalent_pair_list("sushiswap"))


async def get_all_covalent_pairs() -> list[str]:
    return await get_whitelists_from_apis(
        [
            get_uniswap_v2_pairs_covalent,
            get_sushiswap_pairs_covalent,
        ]
    )
