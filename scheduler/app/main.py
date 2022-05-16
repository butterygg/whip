import os

from celery import Celery
import redis

from libs.extract import (get_historical_price_by_address,
                          get_historical_price_by_symbol,
                          get_token_transfers_for_wallet, get_treasury,
                          get_treasury_portfolio)
from libs.pd_inter_calc import portfolio_filler

db = redis.StrictRedis(host=os.environ["REDIS_HOST"])

# add the uniswap treasury is not added already
db.lrem("treasuries", 1, "0x1a9C8182C09F50C8318d769245beA52c32BE35BC")
db.rpush("treasuries", "0x1a9C8182C09F50C8318d769245beA52c32BE35BC")

sched = Celery(
    'app',
    include="app.libs.tasks"
)

sched.config_from_object("app.config.celeryconfig")

if __name__ == "__main__":
    sched.start()

