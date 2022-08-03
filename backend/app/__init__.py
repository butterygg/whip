import os

import redis
import sentry_sdk

if "REDIS_TLS_URL" in os.environ:
    db = redis.Redis.from_url(
        os.environ["REDIS_TLS_URL"], ssl_cert_reqs=None, decode_responses=True
    )
elif "REDIS_URL" in os.environ:
    db = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
else:
    db = redis.Redis(host="redis", decode_responses=True)

if "SENTRY_DSN" in os.environ:
    sentry_sdk.init(
        os.environ["SENTRY_DSN"],
        environment=os.getenv("HEROKU_APP_NAME", "localhost"),
        traces_sample_rate=1.0,
    )
