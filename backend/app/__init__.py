import os

import redis
import sentry_sdk

if "REDIS_TLS_URL" in os.environ:
    db = redis.Redis.from_url(os.environ["REDIS_TLS_URL"], ssl_cert_reqs=None)
elif "REDIS_URL" in os.environ:
    db = redis.Redis.from_url(os.environ["REDIS_URL"])
else:
    db = redis.Redis(host="redis")

if "SENTRY_DSN" in os.environ:
    sentry_sdk.init(
        os.environ["SENTRY_DSN"],
        traces_sample_rate=1.0,
    )
