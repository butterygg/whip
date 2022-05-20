import os

from celery import Celery
import redis
from ujson import dumps
from web3 import Web3
from web3.middleware import geth_poa_middleware

db = redis.StrictRedis(host=os.environ["REDIS_HOST"], decode_responses=True)

# add the uniswap treasury is not added already
db.lrem("treasuries", 1, dumps({"address": "0x78605df79524164911c144801f41e9811b7db73d", "chain_id": 1}))
db.rpush("treasuries", dumps({"address": "0x78605df79524164911c144801f41e9811b7db73d", "chain_id": 1}))

sched = Celery(
    'app',
    include=["app.libs.tasks"],
)

sched.config_from_object("app.config.celeryconfig")

w3 = Web3(Web3.HTTPProvider(os.environ["INFURA"]))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

if __name__ == "__main__":
    sched.start()

