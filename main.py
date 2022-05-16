from celery import Celery

from libs.extract import (
    get_treasury_portfolio, get_treasury,
    get_historical_price_by_address, get_historical_price_by_symbol,
    get_token_transfers_for_wallet
)

from libs.pd_inter_calc import portfolio_filler

sched = Celery(
    'whip',
    include="whip.libs.tasks"
)

sched.config_from_object("whip.config.celeryconfig")

if __name__ == "__main__":
    sched.start()
