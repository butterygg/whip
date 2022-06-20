from asyncio import gather, sleep
from json.decoder import JSONDecodeError
from typing import Coroutine

from celery.utils.log import get_task_logger
from httpx import AsyncClient, HTTPStatusError, RequestError, Timeout

from .storage_helpers import retrieve_token_whitelist, store_token_whitelist


async def retry(method: Coroutine, url: str, await_time: float):
    await sleep(await_time)
    await method(url)


async def get_token_list(token_list: str):
    timeout = Timeout(10.0, read=30.0, connect=15.0)
    logger = get_task_logger(__name__)
    async with AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.get(token_list)
            resp.raise_for_status()
        except HTTPStatusError:
            if resp.status_code == 404:
                logger.warn("404 response for %s, aborting...", token_list)
                return
            logger.error("error receiving token list for %s, retrying...", token_list)
            await retry(client.get, token_list, 10.0)
        except RequestError:
            logger.error("error requesting token list for %s, retrying...", token_list)
            await retry(client.get, token_list, 10.0)

        try:
            whitelist = [
                token["address"]
                for token in resp.json()["tokens"]
                if token["chainId"] == 1
            ]
            store_token_whitelist(whitelist)
        except JSONDecodeError:
            error_str = (
                "unable to decode response from %s"
                + "\n please ensure that `resp.data` is a json formatted string"
            )
            logger.error(error_str, token_list)
            return
        except KeyError:
            logger.error(
                "the token list url given is likely not supported: %s", token_list
            )
            return


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
