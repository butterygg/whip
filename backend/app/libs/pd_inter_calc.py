import datetime
from typing import Optional

import pandas as pd
from dateutil.tz import UTC
from dateutil.utils import today


def make_daily_hist_balance(
    token_symbol: str, hist_transfer_balance: pd.Series, hist_price: pd.Series
) -> Optional[pd.Series]:
    def find_closest_quote(date: datetime.datetime) -> float:
        # For now, quote rates are not going as far back in time than portfolio
        # balances, so just return 0 if no quote
        if date < hist_price.sort_index().index[0]:
            return 0

        earlier_date = date
        while True:
            try:
                return hist_price.loc[earlier_date.strftime("%Y-%m-%d")]
            except KeyError:
                earlier_date -= datetime.timedelta(days=1)
                continue

    _today = today(UTC)
    filled_rows = []
    filled_datetimes = []
    current_balance: float
    current_date: datetime.datetime
    next_date: datetime.datetime

    def fill_until(
        end_date: datetime.datetime,
        start_date: datetime.datetime,
    ):
        _current_date = start_date
        while _current_date < end_date:
            _current_quote = find_closest_quote(_current_date)
            filled_rows.append(current_balance * _current_quote)
            filled_datetimes.append(_current_date)

            _current_date += datetime.timedelta(days=1)
        return _current_date

    rows = list(hist_transfer_balance.to_dict().items())
    if len(rows) < 2:  # [FIXME]
        return None

    for index, row in enumerate(rows):
        current_date = row[0].replace(hour=0, minute=0, second=0, microsecond=0)
        if index < len(rows) - 1:
            next_date = rows[index + 1][0].replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            next_date = current_date + datetime.timedelta(days=1)
            if next_date > _today:
                break

        current_balance = row[1]
        current_date = fill_until(next_date, current_date)

    # Forward fill last dates from last balance change until today with
    # last balance:
    current_date = fill_until(_today + datetime.timedelta(days=1), current_date)

    assert current_date == _today + datetime.timedelta(days=1)

    return pd.Series(
        filled_rows,
        index=pd.Index(filled_datetimes, name="timestamp"),
        name=f"{token_symbol} daily historical balance",
        dtype="float64",
    )
