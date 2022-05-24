from dateutil import parser
from math import log
from typing import Any, Dict, List, Optional
from functools import reduce

import numpy as np
from pandas import DataFrame as DF, MultiIndex, Series

from ..types import Treasury
from ..bitquery import BitqueryTransfer


def add_statistics(
    df: DF,
    column_name: str = "price",
    reverse: bool = True,
    index: Optional[str] = None,
):
    df = df.reset_index()

    """ `returns` calculation section

        `returns` = ln(current_price / previous_price)
    """
    returns = [0]

    for i in range(1, len(df)):
        prev = df.loc[i - 1, column_name]
        current = df.loc[i, column_name]
        if prev == 0 or current == 0:
            returns.append(0)
        else:
            returns.append(log(current / prev))
    df["returns"] = returns

    """ end section
    """

    """ rolling std_dev of `returns` section

        period/window can be conifgurable, 7 days was set
    """

    window = 7
    rolling_window = df["returns"].rolling(window)
    std_dev = rolling_window.std(ddof=0)
    df["std_dev"] = std_dev

    """ end section
    """

    if index is not None:
        df = df.set_index(index)

    if reverse:
        return df.iloc[::-1]

    return df


async def populate_hist_tres_balance(
    asset_trans_history: Dict[str, Any]
) -> Optional[Series]:
    if not asset_trans_history:
        return None
    blocks = asset_trans_history["items"]
    balances: List[float] = []
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


def calculate_risk_contributions(
    treasury: Treasury, augmented_token_hist_prices: DF, start: str, end: str
):
    hist_prices_items = [
        (symbol, hist_prices.set_index("timestamp").loc[start:end].reset_index())
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

    def get_asset(symbol):
        return next(asset for asset in treasury.assets if asset.token_symbol == symbol)

    # Remove ETH from matrix if not an actual portfolio asset
    try:
        get_asset("ETH")
    except StopIteration:
        returns_matrix.drop("ETH", axis=1, inplace=True)

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

    std_dev = np.sqrt(np.dot(np.dot(weights, cov_matrix), weights.T)[0][0])

    marginal_contributions = np.dot(weights, cov_matrix) / std_dev
    component_contributions = np.multiply(marginal_contributions, weights)

    component_percentages = component_contributions / std_dev

    for symbol, percentage in zip(returns_matrix.columns, component_percentages[0]):
        asset = get_asset(symbol)
        asset.risk_contribution = percentage

    return treasury
