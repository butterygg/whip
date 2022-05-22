import datetime
import dateutil
from pytz import UTC
from fastapi import FastAPI


from .libs.tasks import get_assets

app = FastAPI()


@app.get("/portfolio/{address}/{start}/{end}")
async def portfolio(address: str, start=str, end=str):
    start_date = dateutil.parser.parse(start).replace(tzinfo=UTC)
    end_date = dateutil.parser.parse(end).replace(tzinfo=UTC)
    (
        treasury,
        augmented_token_hist_prices,
        asset_hist_balances,
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
        "volatility": 0.1,
        "return vs market": 0.1,
    }

    def get_balance_or_0(df, key):
        try:
            return df.loc[key].balance
        except KeyError:
            return 0

    data = {}
    end = dateutil.utils.today(UTC)
    start = end - datetime.timedelta(days=365)
    date = start
    while True:
        data[date.strftime("%Y-%m-%d")] = sum(
            get_balance_or_0(asset_hist_balances[a.token_symbol], date)
            * a.balance
            / treasury.usd_total
            for a in treasury.assets
        )

        if date == end:
            break
        date += datetime.timedelta(days=1)

    return {"assets": assets, "kpis": kpis, "data": data}
