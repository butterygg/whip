from asyncio import gather
from json.decoder import JSONDecodeError
from typing import Any, Union

from celery.utils.log import get_task_logger
from httpx import AsyncClient, HTTPStatusError, RequestError, Timeout

from .storage_helpers import retrieve_token_whitelist, store_token_whitelist


async def get_token_list(token_list: str) -> list[Union[str, None]]:
    timeout = Timeout(10.0, read=30.0, connect=15.0)
    whitelist = []
    async with AsyncClient(timeout=timeout) as client:
        resp = await client.get(token_list)
        resp.raise_for_status()

        whitelist = [
            token["address"] for token in resp.json()["tokens"] if token["chainId"] == 1
        ]
    return whitelist


async def get_coingecko_token_list() -> tuple[str, list[Union[str, None]]]:
    datasource = "https://tokens.coingecko.com/uniswap/all.json"
    return (datasource, await get_token_list(datasource))


async def get_cmc_token_list() -> tuple[str, list[Union[str, None]]]:
    datasource = "https://api.coinmarketcap.com/data-api/v3/uniswap/all.json"
    return (datasource, await get_token_list(datasource))


async def get_all_token_lists() -> list[Union[str, None]]:
    def flatten_2d(input_list: list[list[Any]]) -> list[Any]:
        payload = []
        for sublist in input_list:
            payload.extend(sublist)
        return payload

    return flatten_2d(
        [
            token_list
            for _, token_list in await gather(
                get_coingecko_token_list(), get_cmc_token_list()
            )
        ]
    )


async def store_and_get_whitelists() -> list[Union[str, None]]:
    try:
        latest_whitelist = await get_all_token_lists()
    except (HTTPStatusError, RequestError, JSONDecodeError, KeyError) as error:
        logger = get_task_logger(__name__)
        if error.__class__ in [HTTPStatusError, RequestError]:
            logger.error("error receiving token list from API", exc_info=error)
            return []
        logger.error("error processing token list API repsonse", exc_info=error)
        return []

    store_token_whitelist(latest_whitelist)
    return latest_whitelist


async def maybe_populate_whitelist() -> list[Union[str, None]]:
    latest_whitelist = list(retrieve_token_whitelist())
    if not latest_whitelist:
        latest_whitelist.extend(await store_and_get_whitelists())
    return latest_whitelist
