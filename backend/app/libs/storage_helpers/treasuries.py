from json import JSONDecodeError
from typing import Union

from celery.utils.log import get_task_logger
from httpx import Client, HTTPStatusError, RequestError, Timeout
from redis import Redis

from .storage_helpers import store_treasury_metadata


def _get_treasury_list() -> list[Union[str, None]]:
    timeout = Timeout(10.0, read=30.0, connect=15.0)
    treasuries = []
    with Client(timeout=timeout) as client:
        resp = client.get(
            "https://api.cryptostats.community/api/v1/treasuries/currentTreasuryPortfolio"
        )
        treasury_portfolios = resp.json()["data"]
    for treasury in treasury_portfolios:
        payload = []
        for address in treasury["metadata"]["treasuries"]:
            payload.append(address)
        if payload:
            treasuries.extend(payload)
    return treasuries


def get_treasury_list(provider: Redis) -> list[Union[str, None]]:
    try:
        return _get_treasury_list()
    except (HTTPStatusError, RequestError, JSONDecodeError, KeyError) as error:
        curr_task = provider.get("curr_task")
        logger = get_task_logger(curr_task if curr_task else __name__)
        if error.__class__ in [HTTPStatusError, RequestError]:
            logger.error("error receiving token list from API", exc_info=error)
            return []
        logger.error("error processing token list API repsonse", exc_info=error)
        return []


def get_and_store_treasury_list(provider: Redis):
    store_treasury_metadata(provider, get_treasury_list(provider))
