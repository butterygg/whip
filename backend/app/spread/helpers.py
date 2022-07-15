import pandas as pd
from pytz import UTC


def make_zeroes(start: str, end: str) -> pd.Series:
    return pd.Series(0, index=pd.date_range(start, end, tz=UTC))
