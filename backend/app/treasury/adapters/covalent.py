# pylint: disable=duplicate-code
import json
from dataclasses import dataclass
from os import getenv
from typing import Any, Dict, Generator, List, Optional

import dateutil
from celery.utils.log import get_logger
from httpx import AsyncClient, HTTPStatusError, Timeout
from pytz import UTC

from ... import db
from ...libs.types import Transfer
from ..models import ERC20, HistoricalPrice, Quote, Treasury


@dataclass
class CovalentTransfer(Transfer):
    pass


CACHE_HASH_TREASURY = "covalent_treasury"
CACHE_KEY_TEMPLATE_PORTFOLIO = "{address}_{chain_id}_{date}"


async def _get_treasury_portfolio(
    treasury_address: str, chain_id: Optional[int] = 1
) -> Dict[str, Any]:
    timeout = Timeout(10.0, read=20.0, connect=25.0)
    async with AsyncClient(timeout=timeout) as client:
        url = (
            f"https://api.covalenthq.com/v1/{chain_id}/address/{treasury_address}/"
            + f"portfolio_v2/?&key=ckey_{getenv('COVALENT_KEY')}"
        )
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()["data"]

    return data


async def get_treasury_portfolio(
    treasury_address: str, chain_id: Optional[int] = 1
) -> Optional[dict[str, Any]]:
    cache_date = dateutil.utils.today(UTC).strftime("%Y-%m-%d")
    cache_key = CACHE_KEY_TEMPLATE_PORTFOLIO.format(
        address=treasury_address, chain_id=chain_id, date=cache_date
    )

    if db.hexists(CACHE_HASH_TREASURY, cache_key):
        return json.loads(db.hget(CACHE_HASH_TREASURY, cache_key))

    try:
        data = await _get_treasury_portfolio(treasury_address, chain_id)
    except (
        HTTPStatusError,
        json.decoder.JSONDecodeError,
        KeyError,
    ) as error:
        logger = get_logger(__name__)
        if error.__class__ is HTTPStatusError:
            logger.error(
                "unable to receive a Covalent `portfolio_v2` API response",
                exc_info=error,
            )
            return {}
        logger.error(
            "error processing Covalent `portfolio_v2` API response", exc_info=error
        )
        return {}

    db.hset(CACHE_HASH_TREASURY, cache_key, json.dumps(data))
    return data


async def get_treasury(portfolio: Dict[str, Any], whitelist: list[str]) -> Treasury:

    windows: List[HistoricalPrice] = []
    for item in portfolio["items"]:
        if item["contract_address"] in whitelist:
            windows.append(
                HistoricalPrice(
                    item["contract_address"],
                    item["contract_name"],
                    item["contract_ticker_symbol"],
                    [
                        Quote(
                            dateutil.parser.parse(holding["timestamp"]),
                            holding["quote_rate"],
                        )
                        for holding in item["holdings"]
                    ],
                )
            )

    # Certain tokens a treasury may hold are noted as spam.
    # To prevent these tokens from corrupting the data,
    # we filter them out via a whitelist provided by tokenlists.org
    assets = [
        ERC20(
            item["contract_name"],
            item["contract_ticker_symbol"],
            item["contract_address"],
            item["holdings"][0]["close"]["quote"],
        )
        for item in portfolio["items"]
        if item["holdings"][0]["close"]["quote"]
        and item["contract_address"] in whitelist
        and item["holdings"]
    ]

    return Treasury(portfolio["address"], assets, windows)


CACHE_HASH_TRANSFERS = "covalent_transfers"
CACHE_KEY_TEMPLATE_TRANSFERS = "{treasury_address}_{contract_address}_{chain_id}_{date}"


async def _get_transfer_data(
    treasury_address: str, contract_address: str, chain_id: int
) -> dict[str, Any]:
    async with AsyncClient(timeout=Timeout(10.0, read=15.0, connect=30.0)) as client:
        resp = await client.get(
            f"https://api.covalenthq.com/v1/{chain_id}/address/{treasury_address}"
            + "/transfers_v2/?quote-currency=USD&format=JSON"
            + f"&contract-address={contract_address}&key=ckey_{getenv('COVALENT_KEY')}"
        )
    resp.raise_for_status()
    return resp.json()["data"]


async def get_transfer_data(
    treasury_address: str, contract_address: str, chain_id: int
) -> Optional[dict[str, Any]]:
    try:
        return await _get_transfer_data(treasury_address, contract_address, chain_id)
    except (
        HTTPStatusError,
        json.decoder.JSONDecodeError,
        KeyError,
    ) as error:
        logger = get_logger(__name__)
        if error.__class__ is HTTPStatusError:
            logger.error(
                "unable to receive a Covalent `transfers_v2` API response",
                exc_info=error,
            )
            return {}
        logger.error(
            "error processing Covalent `transfers_v2` API response", exc_info=error
        )
        return {}


def _gen_transfers(
    asset_trans_history: dict[str, Any]
) -> Generator[CovalentTransfer, None, None]:
    """Yields CovalentTransfers of a given treasury's *partial*, historical token
    balance.

    Parameters
    ---
    asset_trans_history: Dict[str, Any]
        A covalent response from their `transfers_v2` endpoint.
    start: str
        Date to query transfers from. This as well as `end` should be
        formatted as `%Y-%m-%d`
    end: str
        Date to end transfer query

    Notes
    ---
    The historical token balancce of the given treasury is partial
    because, naturaly, covalent's transfers_v2 endpoint only returns
    historical transfers and doesn't return the balance at the time
    of transfer.

    Thus, the balance for a given treasury can only be calculated for
    the date of transfer from the covalent response.

    ---

    The end date allows the historical query to end, returning the
    historical balance from between the start and end dates.
    """
    blocks = asset_trans_history["items"]
    curr_balance = 0.0
    end_index = len(blocks) - 1
    for i in range(end_index, -1, -1):
        transfers = blocks[i]["transfers"]
        decimals = int(transfers[0]["contract_decimals"])

        for transfer in transfers:
            block_date = dateutil.parser.parse(transfer["block_signed_at"])

            if not transfer["quote_rate"]:
                continue
            delta = int(transfer["delta"])
            if transfer["transfer_type"] == "IN":
                curr_balance += delta / 10**decimals if decimals > 0 else 1
                yield CovalentTransfer(balance=curr_balance, timestamp=block_date)
            else:
                curr_balance -= delta / 10**decimals if decimals > 0 else 1
                yield CovalentTransfer(balance=curr_balance, timestamp=block_date)


async def get_token_transfers(
    treasury_address: str, contract_address: str, chain_id: Optional[int] = 1
) -> Optional[list[CovalentTransfer]]:
    cache_date = dateutil.utils.today(UTC).strftime("%Y-%m-%d")
    cache_key = CACHE_KEY_TEMPLATE_TRANSFERS.format(
        treasury_address=treasury_address,
        contract_address=contract_address,
        chain_id=chain_id,
        date=cache_date,
    )

    if db.hexists(CACHE_HASH_TRANSFERS, cache_key):
        balance_hist_data = json.loads(db.hget(CACHE_HASH_TRANSFERS, cache_key))
    else:
        balance_hist_data = await get_transfer_data(
            treasury_address, contract_address, chain_id
        )
        if balance_hist_data:
            db.hset(CACHE_HASH_TRANSFERS, cache_key, json.dumps(balance_hist_data))

    if not balance_hist_data:
        return None

    return list(_gen_transfers(balance_hist_data))
