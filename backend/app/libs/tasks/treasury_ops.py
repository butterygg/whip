# pylint: disable=too-many-locals
from functools import reduce
from math import isclose, log
from typing import Any, Optional

import numpy as np
from dateutil import parser
from pandas import DataFrame as DF
from pandas import MultiIndex, Series

from ..bitquery import BitqueryTransfer
from ..types import Treasury


def add_statistics(
    dataframe: DF,
    column_name: str = "price",
    reverse: bool = True,
    index: Optional[str] = None,
):
    dataframe = dataframe.reset_index()

    # `returns` = ln(current_price / previous_price)
    returns = [0]

    for i in range(1, len(dataframe)):
        prev = dataframe.loc[i - 1, column_name]
        current = dataframe.loc[i, column_name]
        if prev == 0 or current == 0:
            returns.append(0)
        else:
            returns.append(log(current / prev))
    dataframe["returns"] = returns

    # rolling std_dev of `returns` section
    # period/window can be conifgurable, 7 days was set
    window = 7
    rolling_window = dataframe["returns"].rolling(window)
    std_dev = rolling_window.std(ddof=0)
    dataframe["std_dev"] = std_dev

    if index is not None:
        dataframe = dataframe.set_index(index)

    if reverse:
        return dataframe.iloc[::-1]

    return dataframe


async def populate_hist_tres_balance(
    asset_trans_history: dict[str, Any]
) -> Optional[Series]:
    """Return a Series of a given treasury's *partial*, historical token balance.

    The given `asset_trans_history` should be a response from
    `libs.covalent.transfers.get_token_transfers_for_wallet`.

    Parameters
    ---
    asset_trans_history: Dict[str, Any]
        A covalent response from their `transfers_v2` endpoint.
        This should be obtained by using
        `libs.covalent.transfers.get_token_transfers_for_wallet`
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

    the end date allows the historical query to end, returning the
    historical balance from between the start and end dates.
    """
    if not asset_trans_history:
        return None
    blocks = asset_trans_history["items"]
    balances: list[float] = []
    timeseries = []
    address = ""
    symbol = ""
    curr_balance = 0.0
    end_index = len(blocks) - 1
    for i in range(end_index, -1, -1):
        transfers = blocks[i]["transfers"]
        decimals = int(transfers[0]["contract_decimals"])
        if i == end_index:
            address = transfers[0]["contract_address"]
            symbol = transfers[0]["contract_ticker_symbol"]

        for transfer in transfers:
            block_date = parser.parse(transfer["block_signed_at"])

            if not transfer["quote_rate"]:
                continue
            delta = int(transfer["delta"])
            if transfer["transfer_type"] == "IN":
                curr_balance += delta / 10**decimals if decimals > 0 else 1
                balances.append(curr_balance)
            else:
                curr_balance -= delta / 10**decimals if decimals > 0 else 1
                balances.append(curr_balance)

            timeseries.append(block_date)

    index = MultiIndex.from_tuples(
        [(ts, address, symbol) for ts in timeseries],
        names=["timestamp", "contract_address", "contract_symbol"],
    )

    balances = Series(balances, index=index, name="treasury_balances", dtype="float64")

    if len(balances) > 0:
        return balances


def populate_bitquery_hist_eth_balance(eth_transfers: list[BitqueryTransfer]) -> Series:
    index = MultiIndex.from_tuples(
        [
            (bt.timestamp, "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee", "ETH")
            for bt in eth_transfers
        ],
        names=["timestamp", "contract_address", "contract_symbol"],
    )
    return Series(
        (bt.value for bt in eth_transfers),
        index=index,
        name="treasury_balances",
        dtype="float64",
    )


def get_asset(treasury: Treasury, symbol: str):
    return next(asset for asset in treasury.assets if asset.token_symbol == symbol)


def get_returns_matrix(
    treasury: Treasury, augmented_token_hist_prices: dict[str, DF], start: str, end: str
):
    hist_prices_items = [
        # sorting index before querying by daterange to suppress PD Future Warning
        # ; non-monotonic timeseries issue suppresed
        (
            symbol,
            hist_prices.set_index("timestamp")
            .sort_index()
            .loc[start:end]
            .reset_index(),
        )
        for symbol, hist_prices in augmented_token_hist_prices.items()
    ]

    def reducer_on_symbol_and_hist_prices(
        matrix: DF, symbol_and_hist_prices: tuple[str, DF]
    ) -> DF:
        symbol, hist_prices = symbol_and_hist_prices
        return matrix.merge(
            hist_prices[["timestamp", "returns"]].rename(columns={"returns": symbol}),
            on="timestamp",
        )

    returns_matrix = (
        reduce(
            reducer_on_symbol_and_hist_prices,
            hist_prices_items,
            hist_prices_items[0][1][["timestamp", "returns"]].rename(
                columns={"return": hist_prices_items[0][0]}
            ),
        )
        .drop("returns", axis=1)
        .set_index("timestamp")
    )

    # Remove ETH from matrix if not an actual portfolio asset
    try:
        get_asset(treasury, "ETH")
    except StopIteration:
        returns_matrix.drop("ETH", axis=1, inplace=True)

    return returns_matrix


def calculate_risk_contributions(
    treasury: Treasury, augmented_token_hist_prices: dict[str, DF], start: str, end: str
):
    returns_matrix = get_returns_matrix(
        treasury, augmented_token_hist_prices, start, end
    )

    current_balances = {asset.token_symbol: asset.balance for asset in treasury.assets}
    weights = np.array(
        [
            np.fromiter(
                (current_balances[symbol] for symbol in returns_matrix.columns), float
            )
            / treasury.usd_total
        ]
    )

    cov_matrix = returns_matrix.cov()

    std_dev = np.sqrt(weights.dot(cov_matrix).dot(weights.T))

    marginal_contributions = weights.dot(cov_matrix) / std_dev[0][0]
    component_contributions = np.multiply(marginal_contributions, weights)

    summed_component_contributions = np.sum(component_contributions)

    assert isclose(
        summed_component_contributions, std_dev[0][0], rel_tol=0.0001
    ), "error in calculations"
    # print(f"component_contributions: {component_contributions}")

    component_percentages = component_contributions / std_dev[0][0]

    for symbol, percentage in zip(returns_matrix.columns, component_percentages[0]):
        asset = get_asset(treasury, symbol)
        asset.risk_contribution = percentage

    return treasury


def calculate_correlations(
    treasury: Treasury, augmented_token_hist_prices: dict[str, DF], start: str, end: str
):
    returns_matrix = get_returns_matrix(
        treasury, augmented_token_hist_prices, start, end
    )

    return returns_matrix.corr()


def apply_spread_percentages(
    asset_hist_balances: dict[str, DF],
    spread_token_symbol: str,
    spread_percentage: int,
    start: str,
) -> dict[str, DF]:
    def get_default_balance(histbal: DF, date: str) -> float:
        try:
            return histbal.set_index("timestamp").sort_index().loc[date].balance
        except KeyError:
            return 0

    start_balance = sum(
        get_default_balance(asset_hist_balance, start)
        for asset_hist_balance in asset_hist_balances.values()
    )
    start_balance_except_spread_token = sum(
        get_default_balance(asset_hist_balance, start)
        for symbol, asset_hist_balance in asset_hist_balances.items()
        if symbol != spread_token_symbol
    )

    if spread_token_symbol not in asset_hist_balances:
        spread_token_hist_balance = next(iter(asset_hist_balances.values())).copy()
        spread_token_hist_balance.balance = start_balance * spread_percentage / 100.0
        downsize_factor = (100 - spread_percentage) / 100.0

    else:
        spread_token_hist_balance = asset_hist_balances[spread_token_symbol]
        spread_token_hist_balance.balance += start_balance * spread_percentage / 100.0

        downsize_factor = (
            1
            - spread_percentage
            / 100.0
            * start_balance
            / start_balance_except_spread_token
        )

    def downsize(asset_hist_balance: DF):
        spread_asset_hist_balance = asset_hist_balance.copy()
        spread_asset_hist_balance.balance *= downsize_factor
        return spread_asset_hist_balance

    spread_asset_hist_balances = {
        symbol: downsize(asset_hist_balance)
        for symbol, asset_hist_balance in asset_hist_balances.items()
    }
    spread_asset_hist_balances[spread_token_symbol] = spread_token_hist_balance

    return spread_asset_hist_balances
