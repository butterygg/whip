from concurrent.futures import ThreadPoolExecutor
from dateutil import parser
from math import log, floor
from typing import Any, Dict, List, Tuple

from asgiref.sync import async_to_sync
from dotenv import load_dotenv
from pandas import DataFrame as DF, MultiIndex, Series, to_datetime
from ujson import loads
from web3 import Web3

from . import (
    get_coin_hist_price,
    coingecko_hist_df,
    get_treasury,
    get_treasury_portfolio,
    get_token_transfers_for_wallet,
    get_historical_price_by_symbol,
    portfolio_filler,

    db,
    sched,
    w3
)

load_dotenv()

async def clean_hist_prices(df: DF):
    symbol = df.index[0][2]
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

# [XXX] cache and run every day
async def get_hist_prices_for_portfolio(symbol: str):
    covalent_resp = await get_historical_price_by_symbol(
        symbol,
        (2, "years")
    )

    if not covalent_resp:
        return

    contract_address = covalent_resp["prices"][0]["contract_metadata"]["contract_address"]
    decimals = covalent_resp["contract_decimals"]
    indexes = MultiIndex.from_tuples(
        [
            (ts, contract_address, symbol, decimals) for ts
            in [ to_datetime((price["date"]), utc=True) for price in covalent_resp["prices"] ]
        ],
        names=["timestamp", "address", "symbol", "decimals"]
    )

    return DF(
        data=covalent_resp["prices"],
        index=indexes
    ).drop(["contract_metadata", "date"], axis=1)

async def populate_hist_tres_balance(asset_trans_history: Dict[str, Any]):
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
                curr_balance += delta / 10 ** decimals if decimals > 0 else 1
                balances.append(curr_balance)
            else:
                curr_balance -= delta / 10 ** decimals if decimals > 0 else 1
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
        name="treasury_balances",
        dtype="float64"
    )

    if len(balances) > 0:
        return balances

@sched.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(30.0, load_treasury.s(), name="reload treasury data")

@sched.task
def load_treasury():
    with db.pipeline() as pipe:
        # key: `treasuries` contains an array of treasury metadata objects
        treasuries: List[str] = db.lrange("treasuries", 0, -1)

        for raw_treasury in treasuries:
            # contains treasury metadata; treasury's address, chain_id, etc.
            treasury_meta: Dict[str, Any] = loads(raw_treasury)
            portfolio = async_to_sync(get_treasury_portfolio)(treasury_meta["address"], treasury_meta.get("chain_id"))

            treasury = async_to_sync(get_treasury)(portfolio)
            treasury_assets = DF(data=treasury.assets, index=[asset["token_symbol"] for asset in treasury.assets])
            treasury_assets.drop(["token_name", "token_symbol"], axis=1, inplace=True)
            treasury_assets.rename_axis("token_symbol", inplace=True)

            asset_transfers = [
                async_to_sync(get_token_transfers_for_wallet)(treasury.address, token_contract)
                for token_contract in treasury_assets["token_address"]
            ]

            coroutines = [
                async_to_sync(populate_hist_tres_balance)(trans_history)
                for trans_history in asset_transfers
            ]

            historical_treasury_balance: List[Series] = []
            for coro in coroutines:
                result: Series = coro

                if type(result) is Series:
                    historical_treasury_balance.append(result) if not result.empty else None
            
            print(f"no. of assets: {len(treasury_assets)}")
            raw_hist_prices: List[Tuple[str, str, List[List[int]]]] = [
                async_to_sync(get_coin_hist_price)(address, sym, (2, "years"))
                for address, sym in zip(treasury_assets["token_address"], treasury_assets.index.values.tolist())
            ]

            coroutines = [
                coingecko_hist_df(address, symbol, resp)
                for address, symbol, resp in raw_hist_prices if resp
            ]

            historical_price_for_portfolio_assets: List[DF] = []
            index = 0
            asset_dict = { }
            for coro in coroutines:
                result = coro
                if type(result) is not DF:
                    continue
                result = result.reset_index()

                for asset in historical_treasury_balance:
                    asset = asset.reset_index()
                    symbol: str = asset["contract_symbol"][0]
                    if symbol.find(result["symbol"][0]) > -1:
                        asset_dict[symbol] = index
                        index += 1
                        break

                historical_price_for_portfolio_assets.append(result) if not result.empty else None
            
            cleaned_hist_prices = []
            # print(treasury_assets)
            for df in historical_price_for_portfolio_assets:
                balances = None

                # print(df)
                cleaned_df: DF = async_to_sync(clean_hist_prices)(df)
                index = asset_dict.get(cleaned_df["symbol"][0])
                if index is not None:
                    balances = historical_treasury_balance[index]
                else:
                    continue
                cleaned_hist_prices.append(cleaned_df)

                quote_rates = Series(data=cleaned_df["price"])
                quote_rates.index = to_datetime(cleaned_df["timestamp"])


                print(f"piping results for {cleaned_df['symbol'][0]}")
                if len(balances) >= 2:
                    contract_address = balances.index.get_level_values(1).to_list()
                    quote_rates = quote_rates.iloc[::-1]
                    portfolio_performance = portfolio_filler(balances, quote_rates, contract_address[0])
                    print(f"portfolio perf for {treasury.address[:6] + '_' + cleaned_df['symbol'][0]}: {portfolio_performance[-5:]}")
                    pipe.hset("balances", treasury.address[:6] + "_" + cleaned_df["symbol"][0], portfolio_performance.to_json(orient='records'))
                pipe.hset("hist_prices", cleaned_df["symbol"][0], cleaned_df.to_json(orient='records'))

            # pipe.hset("balances", treasury.address[:6] + "_" + "ETH", get_hist_native_balances(treasury.address).to_json(orient='records'))
            pipe.set(treasury.address, treasury_assets.to_json(orient='records'))
        pipe.execute()
        print("success")
