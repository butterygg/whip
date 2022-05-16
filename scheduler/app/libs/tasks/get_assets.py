from asyncio import as_completed
from dateutil import parser
from math import log
from os import getenv
from typing import Any, Dict, List

from dotenv import load_dotenv
from pandas import DataFrame as DF, MultiIndex, Series, to_datetime
# from redis import Redis
from ujson import dumps, loads

from . import (
    get_treasury,
    get_treasury_portfolio,
    get_token_transfers_for_wallet,
    get_historical_price_by_symbol,
    portfolio_filler,

    db,
    sched
)

load_dotenv()

async def clean_hist_prices(df: DF):
    symbol_level = df.index.get_level_values(2)
    symbol = symbol_level[0]
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
            print(f"\tsymbol: {symbol}\n\tindex: {i}\n\tcurr_price: {df.loc[i - 1, 'price']}\n\tprev_price: {df.loc[i, 'price']}")
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

async def get_hist_prices_for_portfolio(symbol: str):
    covalent_resp = await get_historical_price_by_symbol(
        symbol,
        (2, "years")
    )

    if not covalent_resp:
        return

    indexes = MultiIndex.from_tuples(
        [
            (ts, address, symbol) for ts, address
            in zip(
                [ price["date"] for price in covalent_resp["prices"] ],
                [ price["contract_metadata"]["contract_address"] for price in covalent_resp["prices"] ]
            )
        ],
        names=["timestamp", "address", "symbol"]
    )

    return DF(
        data=covalent_resp["prices"],
        index=indexes
    ).drop(["contract_metadata", "date"], axis=1)

async def populate_hist_tres_balance(asset_trans_history: Dict[str, Any]):
    if not asset_trans_history:
        return None
    blocks = asset_trans_history["items"]
    balances = []
    timeseries = []
    address = ""
    symbol = ""
    curr_balance = 0.0
    end_index = len(blocks) - 1
    for i in range(end_index, -1, -1):
        transfers = blocks[i]["transfers"]
        if i == end_index:
            address = transfers[0]["contract_address"]
            symbol = transfers[0]["contract_ticker_symbol"]

        for transfer in transfers:
            if not transfer["quote_rate"]:
                continue
            delta = int(transfer["delta"])
            if transfer["transfer_type"] == "IN":
                curr_balance += delta / 1e18
                balances.append(curr_balance)
            else:
                curr_balance -= delta / 1e18
                balances.append(curr_balance)

            timeseries.append(parser.parse(transfer["block_signed_at"]))

    index = MultiIndex.from_tuples(
        [
            (ts, address, symbol)
            for ts in timeseries
        ],
        names=["timestamp", "contract_address", "contract_symbol"] 
    )

    balances = Series(
        balances,
        index=index,
        name="treasury_balances"
    )

    if len(balances) > 0:
        return balances

@sched.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(30.0, load_treasury.s(), name="reload treasury data")

@sched.task
async def load_treasury():    
    with db.pipeline() as pipe:
        # key: `treasuries` contains an array of treasury addresses
        treasuries: List[str] = pipe.lrange("treasuries")

        for raw_treasury in treasuries:
            # contains treasury metadata; treasury's address, chain_id, etc.
            treasury_meta: Dict[str, Any] = loads(raw_treasury)
            portfolio = await get_treasury_portfolio(treasury_meta["address"], treasury_meta.get("chain_id"))

            treasury = await get_treasury(portfolio)
            treasury_assets = DF(data=treasury.assets, index=[asset["token_symbol"] for asset in treasury.assets])
            treasury_assets.drop(["token_name", "token_symbol"], axis=1, inplace=True)
            treasury_assets.rename_axis("token_symbol", inplace=True)

            asset_transfers = [
                await get_token_transfers_for_wallet(treasury.address, token_contract)
                for token_contract in treasury_assets["token_address"]
            ]

            coroutines = as_completed([
                populate_hist_tres_balance(trans_history)
                for trans_history in asset_transfers
            ])

            historical_treasury_balance: List[DF] = []
            for coro in coroutines:
                result = await coro

                historical_treasury_balance.append(result) if result else None
            
            coroutines = as_completed([
                get_hist_prices_for_portfolio(symbol)
                for symbol in treasury_assets.index.values
            ])

            historical_price_for_portfolio_assets: List[DF] = []
            index = 0
            asset_dict = { }
            for coro in coroutines:
                result = await coro

                for asset in historical_treasury_balance:
                    symbol: str = asset["symbol"][0]
                    if symbol.find(result["symbol"]) > -1:
                        asset_dict[symbol] = index
                        break
                index += 1

                historical_price_for_portfolio_assets.append(result) if result else None

            cleaned_hist_prices = []
            for df in historical_price_for_portfolio_assets:
                balances = None
                index = asset_dict.get(cleaned_df["symbol"])
                if index is not None:
                    balances = historical_treasury_balance[index]
                else:
                    continue

                cleaned_df = await clean_hist_prices(df)
                cleaned_hist_prices.append(cleaned_df)

                quote_rates = Series(data=cleaned_df["price"])
                quote_rates.index = to_datetime(cleaned_df["timestamp"])


                pipe.hset("balances", treasury.address[:6] + cleaned_df["symbol"], portfolio_filler(balances, quote_rates))
                pipe.hset("hist_prices", cleaned_df["symbol"], cleaned_df.to_json(orient='records'))

            pipe.set(treasury.address, treasury_assets.to_json(orient='records'))

        pipe.execute()

    # db.close()
