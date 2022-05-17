import os

import redis
from fastapi import FastAPI

from libs.extract import (
    get_historical_price_by_address,
    get_historical_price_by_symbol,
    get_token_transfers_for_wallet,
    get_treasury,
    get_treasury_portfolio,
)
from libs.pd_inter_calc import portfolio_filler

app = FastAPI()

if "REDIS_TLS_URL" in os.environ:
    db = redis.StrictRedis.from_url(os.environ["REDIS_TLS_URL"])
elif "REDIS_URL" in os.environ:
    db = redis.StrictRedis.from_url(os.environ["REDIS_URL"])
else:
    db = redis.StrictRedis(host=os.environ["REDIS_HOST"])


@app.get("/testapi")
def testapi():
    return {
        "UNI": {
            "allocation": 0.95,
            "volatility": 0.7,
            "riskContribution": 0.99,
        },
        "DAI": {
            "allocation": 0.05,
            "volatility": 0.01,
            "riskContribution": 0.01,
        },
    }
