import os

import redis

if "REDIS_TLS_URL" in os.environ:
    db = redis.Redis.from_url(os.environ["REDIS_TLS_URL"], ssl_cert_reqs=None)
elif "REDIS_URL" in os.environ:
    db = redis.Redis.from_url(os.environ["REDIS_URL"])
else:
    db = redis.Redis(host="redis")
