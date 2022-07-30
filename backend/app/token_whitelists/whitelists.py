from json.decoder import JSONDecodeError
from typing import Union

import redis
from celery.utils.log import get_task_logger
from httpx import HTTPStatusError, RequestError

from .adapters import (
    get_all_covalent_pairs,
    get_all_tokenlists,
    retrieve_token_whitelist,
    store_token_whitelist,
)


async def store_and_get_covalent_pairs_whitelist(
    provider: Union[redis.Redis, redis.client.Pipeline]
) -> list[str]:
    try:
        latest_whitelist = await get_all_covalent_pairs()
    except (HTTPStatusError, RequestError, JSONDecodeError, KeyError) as error:
        logger = get_task_logger(__name__)
        log_args = (
            ("receiving pairs", "Covalent API")
            if error.__class__ in [HTTPStatusError, RequestError]
            else ("processing pairs", "Covalent API repsonse")
        )
        logger.error("error %s from %s", *log_args, exc_info=error)
        return []

    store_token_whitelist(latest_whitelist, provider)
    return latest_whitelist


async def store_and_get_tokenlist_whitelist(
    provider: Union[redis.Redis, redis.client.Pipeline]
) -> list[str]:
    try:
        latest_whitelist = await get_all_tokenlists()
    except (HTTPStatusError, RequestError, JSONDecodeError, KeyError) as error:
        logger = get_task_logger(__name__)
        if error.__class__ in [HTTPStatusError, RequestError]:
            logger.error("error receiving token list from API", exc_info=error)
            return []
        logger.error("error processing token list API repsonse", exc_info=error)
        return []

    store_token_whitelist(latest_whitelist, provider)
    return latest_whitelist


async def maybe_populate_whitelist(
    provider: Union[redis.Redis, redis.client.Pipeline]
) -> list[Union[str, None]]:
    latest_whitelist = list(retrieve_token_whitelist(provider))
    if not latest_whitelist:
        latest_whitelist.extend(await store_and_get_tokenlist_whitelist(provider))
        latest_whitelist.extend(await store_and_get_covalent_pairs_whitelist(provider))
    return latest_whitelist
