import os
import redis


if "REDIS_TLS_URL" in os.environ:
    db = redis.StrictRedis.from_url(os.environ["REDIS_TLS_URL"])
elif "REDIS_URL" in os.environ:
    db = redis.StrictRedis.from_url(os.environ["REDIS_URL"])
else:
    db = redis.StrictRedis(host="redis")
