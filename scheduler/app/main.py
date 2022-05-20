import os

from celery import Celery
import redis
from ujson import dumps

db = redis.StrictRedis(host=os.environ["REDIS_HOST"], decode_responses=True)

# add the uniswap treasury is not added already
db.lrem("treasuries", 1, dumps({"address": "0x78605df79524164911c144801f41e9811b7db73d", "chain_id": 1}))
db.rpush("treasuries", dumps({"address": "0x78605df79524164911c144801f41e9811b7db73d", "chain_id": 1}))

sched = Celery(
    'app',
    include=["app.libs.tasks"],
)

sched.config_from_object("app.config.celeryconfig")

if __name__ == "__main__":
    sched.start()

