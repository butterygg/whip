from asyncio import gather, sleep
from json.decoder import JSONDecodeError
from logging import getLogger
from typing import Coroutine, Union

import redis
from celery.utils.log import get_task_logger
from httpx import AsyncClient, HTTPStatusError, RequestError, Timeout

from .storage_helpers import retrieve_token_whitelist, store_token_whitelist


async def retry(method: Coroutine, url: str, await_time: float):
    await sleep(await_time)
    await method(url)


async def get_token_list(
    token_list: str, provider: Union[redis.Redis, redis.client.Pipeline]
):
    timeout = Timeout(10.0, read=30.0, connect=15.0)
    task_id = (
        provider.get("curr_task")
        if provider.__class__ is redis.Redis
        else provider.immediate_execute_command("GET", "curr_task")
    )
    logger = get_task_logger(task_id) if task_id else getLogger(__name__)
    async with AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.get(token_list)
            resp.raise_for_status()
        except HTTPStatusError:
            if resp.status_code == 404:
                logger.warning("404 response for %s, aborting...", token_list)
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
            store_token_whitelist(whitelist, provider)
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


async def get_coingecko_token_list(provider: Union[redis.Redis, redis.client.Pipeline]):
    await get_token_list("https://tokens.coingecko.com/uniswap/all.json", provider)


async def get_cmc_token_list(provider: Union[redis.Redis, redis.client.Pipeline]):
    await get_token_list(
        "https://api.coinmarketcap.com/data-api/v3/uniswap/all.json", provider
    )


async def get_all_token_lists(provider: Union[redis.Redis, redis.client.Pipeline]):
    await gather(
        get_coingecko_token_list(provider),
        get_cmc_token_list(provider),
    )


async def maybe_populate_whitelist(provider: redis.Redis) -> list[str]:
    token_whitelist = retrieve_token_whitelist(provider)
    if not token_whitelist:
        await get_all_token_lists(provider)
        token_whitelist = retrieve_token_whitelist(provider)
    return token_whitelist
