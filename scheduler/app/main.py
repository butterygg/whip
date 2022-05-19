import os

from celery import Celery
import redis
from ujson import dumps

db = redis.StrictRedis(host=os.environ["REDIS_HOST"], decode_responses=True)

# # add the uniswap treasury is not added already
# db.lrem("treasuries", 1, "0x1a9C8182C09F50C8318d769245beA52c32BE35BC")
# db.rpush("treasuries", dumps({"address": "0x1a9C8182C09F50C8318d769245beA52c32BE35BC", "chain_id": 1}))

sched = Celery(
    'app',
    include=["app.libs.tasks"],
)

sched.config_from_object("app.config.celeryconfig")

if __name__ == "__main__":
    sched.start()

