import datetime
import dateutil
from pytz import UTC
from fastapi import FastAPI


from .libs.tasks import get_assets

app = FastAPI()


@app.get("/portfolio/{address}/{start}")
async def portfolio(address: str, start=str):
    start_date = dateutil.parser.parse(start).replace(tzinfo=UTC)
    end_date = dateutil.utils.today(UTC) - datetime.timedelta(days=1)
    end = end_date.strftime("%Y-%m-%d")
    (
        treasury,
        augmented_token_hist_prices,
        asset_hist_balances,
        augmented_total_balance,
    ) = await get_assets.build_treasury_with_assets(address, 1, start, end)

    histprices = {
        symbol: athp.set_index("timestamp").loc[start:end]
        for symbol, athp in augmented_token_hist_prices.items()
    }
    totalbalance = augmented_total_balance.loc[start:end]

    assets = {
        a.token_symbol: {
            "allocation": a.balance / treasury.usd_total,
            "volatility": histprices[a.token_symbol]["std_dev"].mean(),
            "riskContribution": a.risk_contribution,
        }
        for a in treasury.assets
    }

    if (start not in totalbalance.index) or (totalbalance.loc[start].balance == 0):
        market_return = "Infinity"
    else:
        eth_series = histprices["ETH"]
        market_return = (
            totalbalance.loc[end].balance - totalbalance.loc[start].balance
        ) / totalbalance.loc[start].balance - (
            eth_series.loc[end].price - eth_series.loc[start].price
        ) / eth_series.loc[
            start
        ].price

    kpis = {
        "total value": treasury.usd_total,
        "volatility": totalbalance.std_dev.mean(),
        "return vs market": market_return,
    }

    data = {
        timestamp.to_pydatetime().strftime("%Y-%m-%d"): balance
        for timestamp, balance in totalbalance.to_dict()["balance"].items()
    }

    return {"assets": assets, "kpis": kpis, "data": data}
