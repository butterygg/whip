from dateutil import parser
from math import log
from typing import Any, Dict, List, Optional

from pandas import DataFrame as DF, MultiIndex, Series


async def clean_hist_prices(df: DF):
    symbol = df["symbol"][0]
    df = df.reset_index()

    """ `returns` calculation section

        `returns` = ln(current_price / previous_price)
    """
    returns = []
    for i in range(1, len(df)):
        try:
            # current price is df[i - 1] since `loc` descends the DF
            returns.append(log(df.loc[i - 1, "price"] / df.loc[i, "price"]))
        except Exception as e:
            print("misbehaving case: \n")
            print(
                f"\tsymbol: {symbol}\n\tindex: {i}\n\tcurr_price: {df.loc[i - 1, 'price']}\n\tprev_price: {df.loc[i, 'price']}"
            )
            returns.append(None)
    returns.append(0)
    df["returns"] = returns

    """ end section
    """

    """ rolling std_dev of `returns` section

        period/window can be conifgurable, 7 days was set
    """

    window = 7
    rolling_window = df["returns"].iloc[::-1].rolling(window)
    std_dev = rolling_window.std(ddof=0)
    df["std_dev"] = std_dev

    """ end section
    """

    df = df.iloc[::-1]

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
            if not transfer["quote_rate"]:
                continue
            delta = int(transfer["delta"])
            if transfer["transfer_type"] == "IN":
                curr_balance += delta / 10**decimals if decimals > 0 else 1
                balances.append(curr_balance)
            else:
                curr_balance -= delta / 10**decimals if decimals > 0 else 1
                balances.append(curr_balance)

            timeseries.append(parser.parse(transfer["block_signed_at"]))

    index = MultiIndex.from_tuples(
        [(ts, address, symbol) for ts in timeseries],
        names=["timestamp", "contract_address", "contract_symbol"],
    )

    balances = Series(balances, index=index, name="treasury_balances", dtype="float64")

    if len(balances) > 0:
        return balances
