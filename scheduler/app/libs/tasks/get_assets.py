from concurrent.futures import ThreadPoolExecutor
from dateutil import parser
from math import log, floor
from typing import Any, Dict, List, Tuple

from asgiref.sync import async_to_sync
from dotenv import load_dotenv
from pandas import DataFrame as DF, MultiIndex, Series, to_datetime
from ujson import loads

from . import (
    Treasury,

    coingecko_hist_df,
    get_coin_hist_price,
    get_treasury,
    get_treasury_portfolio,
    get_token_transfers_for_wallet,
    portfolio_filler,

    db,
    sched,
    w3
)
from .treasury_ops import *

load_dotenv()

async def make_treasury(treasury_address: str, chain_id: int) -> Treasury:
    return await get_treasury(await get_treasury_portfolio(treasury_address, chain_id))


def filter_out_small_assets(treasury: Treasury):
    treasury.assets = [
        asset for asset in treasury.assets
        if asset.balance/treasury.usd_total >= 0.5/100
    ]
    return treasury

async def get_sparse_asset_hist_balances(treasury: Treasury) -> dict[str, Series]:
    asset_contract_addresses = {
        asset.token_symbol: asset.token_address for asset in treasury.assets
    }
    transfer_histories = {
        symbol: await get_token_transfers_for_wallet(treasury.address, asset_contract_address)
        for symbol, asset_contract_address in asset_contract_addresses.items()
    }
    maybe_sparse_asset_hist_balances = {
        symbol: await populate_hist_tres_balance(transfer_history)
        for symbol, transfer_history in transfer_histories.items()
    }
    return {
        symbol: hist
        for symbol, hist in maybe_sparse_asset_hist_balances.items()
        if hist is not None and not hist.empty
    }


async def get_token_hist_prices(treasury: Treasury) -> dict[str, DF]:
    maybe_hist_prices = {
        asset.token_symbol: await get_hist_prices_for_portfolio(asset.token_symbol)
        for asset in treasury.assets
    }
    return {symbol: hist for symbol, hist in maybe_hist_prices.items() if hist is not None}

async def augment_token_hist_prices(
    token_hist_prices: dict[str, DF]
) -> dict[str, DF]:
    return {
        symbol: await clean_hist_prices(token_hist_price)
        for symbol, token_hist_price in token_hist_prices.items()
    }

async def fill_asset_hist_balances(
    sparse_asset_hist_balances: dict[str, Series],
    augmented_token_hist_prices: dict[str, DF]
) -> dict[str, DF]:
    def fill_asset_hist_balance(symbol, augmented_token_hist_price):
        if (
            symbol not in sparse_asset_hist_balances or
            len(sparse_asset_hist_balances[symbol]) < 2
        ):
            return None
        quote_rates = Series(data=augmented_token_hist_price["price"])
        quote_rates.index = to_datetime(augmented_token_hist_price["timestamp"])
        return portfolio_filler(sparse_asset_hist_balances[symbol], quote_rates)

    maybe_asset_hist_balance = {
        symbol: fill_asset_hist_balance(symbol, augmented_token_hist_price)
        for symbol, augmented_token_hist_price in augmented_token_hist_prices.items()
    }
    return {
        symbol: asset_hist_balance
        for symbol, asset_hist_balance in maybe_asset_hist_balance.items()
        if asset_hist_balance is not None
    }


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

            treasury = filter_out_small_assets(async_to_sync(make_treasury)(treasury_meta["address"], 1))
            treasury_assets = DF(data=treasury.assets, index=[asset.token_symbol for asset in treasury.assets])
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
            for df in historical_price_for_portfolio_assets:
                balances = None

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
                    quote_rates = quote_rates.iloc[::-1]
                    portfolio_performance = portfolio_filler(balances, quote_rates)
                    print(f"portfolio perf for {treasury.address[:6] + '_' + cleaned_df['symbol'][0]}: {portfolio_performance[-5:]}")
                    pipe.hset("balances", treasury.address[:6] + "_" + cleaned_df["symbol"][0], portfolio_performance.to_json(orient='records'))
                pipe.hset("hist_prices", cleaned_df["symbol"][0], cleaned_df.to_json(orient='records'))

            # pipe.hset("balances", treasury.address[:6] + "_" + "ETH", get_hist_native_balances(treasury.address).to_json(orient='records'))
            pipe.set(treasury.address, treasury_assets.to_json(orient='records'))
        pipe.execute()
        print("success")
