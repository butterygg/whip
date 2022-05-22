import datetime
import dateutil
from pytz import UTC
from fastapi import FastAPI


from .libs.tasks import get_assets

app = FastAPI()


@app.get("/portfolio/{address}/{start}")
async def portfolio(address: str, start=str):
    start_date = dateutil.parser.parse(start).replace(tzinfo=UTC)
    (
        treasury,
        augmented_token_hist_prices,
        asset_hist_balances,
        augmented_total_balance,
    ) = await get_assets.build_treasury_with_assets(address, 1)

    assets = {
        a.token_symbol: {
            "allocation": a.balance / treasury.usd_total,
            "volatility": augmented_token_hist_prices[a.token_symbol]["std_dev"].mean(),
            "riskContribution": 0.123,
        }
        for a in treasury.assets
    }
    kpis = {
        "total value": treasury.usd_total,
        "volatility": augmented_total_balance["std_dev"].mean(),
        "return vs market": 0.1,
    }

    data = {
        timestamp.to_pydatetime().strftime("%Y-%m-%d"): balance
        for timestamp, balance in augmented_total_balance.to_dict()["balance"].items()
    }

    return {"assets": assets, "kpis": kpis, "data": data}
