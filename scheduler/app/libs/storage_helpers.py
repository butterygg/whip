import ujson

from . import db


CHAIN_ID = 1

def store_treasur_meta(address: str):
    stored_addresses = [ujson.loads(t)['address'] for t in db.lrange('treasuries', 0, -1)]
    if address in stored_addresses:
        return
    db.rpush({'address': address, 'chain_id': CHAIN_ID})


def retrieve_treasuries_meta() -> list[tuple[str, int]]:
    treasuries_meta = [
        ujson.loads(t)
        for t in db.lrange('treasuries', 0, -1)
    ]
    return [(tm['address'], tm.get('chain_id', CHAIN_ID)) for tm in treasuries_meta]