import os

import redis
from fastapi import FastAPI

from libs.extract import (get_historical_price_by_address,
                          get_historical_price_by_symbol,
                          get_token_transfers_for_wallet, get_treasury,
                          get_treasury_portfolio)
from libs.pd_inter_calc import erc20_portfolio_filler

app = FastAPI()
db = redis.StrictRedis(host=os.environ["REDIS_HOST"])
