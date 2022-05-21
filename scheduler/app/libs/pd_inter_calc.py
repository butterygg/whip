from datetime import datetime, timedelta
from dateutil.utils import today
from dateutil.tz import UTC

from pandas import DataFrame as DF, Index, Series


def portfolio_filler(portfolio_balances: Series, quote_rates: Series) -> Series:
    def find_closest_quote(date: datetime):
        earlier_date = date
        while True:
            try:
                return quote_rates.loc[earlier_date.strftime("%Y-%m-%d")]
            except KeyError:
                earlier_date = earlier_date - timedelta(days=1)
                continue

    filled_rows = []
    filled_dates = []
    rows = list(portfolio_balances.to_dict().items())
    index = 0
    if len(rows) < 2:
        return
    for date, balance in rows:
        curr_date: datetime = date[0]
        next_date: datetime = rows[index + 1][0][0]

        curr_balance = balance
        while curr_date < next_date:
            curr_quote = find_closest_quote(curr_date)
            filled_rows.append(curr_balance * curr_quote)
            filled_dates.append(curr_date)

            curr_date += timedelta(days=1)

        index += 1
        if index == len(rows) - 1:
            curr_date = today(UTC)
            curr_balance = rows[-1][1]

            prev_date: datetime = filled_dates[-1]
            prev_date += timedelta(days=1)
            while prev_date <= curr_date:

                curr_quote = find_closest_quote(prev_date)
                filled_rows.append(curr_balance * curr_quote)
                filled_dates.append(prev_date)

                prev_date += timedelta(days=1)
            break

    return DF(
        [[ts, value] for ts, value in zip(filled_dates, filled_rows)],
        index=Index(filled_dates, name="timestamp"),
        columns=["timestamp", "balance"],
    )
