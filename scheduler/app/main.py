from fastapi import FastAPI

from .libs.tasks import get_assets


app = FastAPI()


@app.get("/portfolio/{address}")
async def portfolio(address: str):
    (
        treasury,
        augmented_token_hist_prices,
        asset_hist_balances,
    ) = await get_assets.build_treasury_with_assets(address, 1)
    return treasury.__dict__

    # assets = {
    #     "UNI": {
    #         "allocation": 0.95,
    #         "volatility": 0.7,
    #         "riskContribution": 0.99,
    #     },
    #     "DAI": {
    #         "allocation": 0.05,
    #         "volatility": 0.01,
    #         "riskContribution": 0.01,
    #     },
    # }
