from asyncio import gather
from typing import Any, Coroutine


async def get_whitelists_from_apis(api_getters: list[Coroutine]) -> list[str]:
    def flatten_2d(input_list: list[list[Any]]) -> list[Any]:
        payload = []
        for sublist in input_list:
            payload.extend(sublist)
        return payload

    return flatten_2d(
        [
            whitelist
            for _, whitelist in await gather(*[_getter() for _getter in api_getters])
        ]
    )
