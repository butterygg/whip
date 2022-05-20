from datetime import datetime, timedelta
from dateutil.utils import today
from dateutil.tz import UTC

from pandas import DataFrame as DF, Index, Series

def portfolio_filler(portfolio_balances: Series, quote_rates: Series, contract_address: str = None) -> Series:
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
            try:
                curr_quote = quote_rates.loc[curr_date.strftime("%Y-%m-%d")]
            except KeyError as e:
                print(f"there is likely a gap in quote prices for this asset at {curr_date.strftime('%Y-%m-%d')}")
                curr_date += timedelta(days=1)
                continue
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
                try:
                    curr_quote = quote_rates.loc[prev_date.strftime("%Y-%m-%d")]
                except KeyError as e:
                    prev_date += timedelta(days=1)
                    continue
                filled_rows.append(curr_balance * curr_quote)
                filled_dates.append(prev_date)

                prev_date += timedelta(days=1)
            break

    return DF([[ts, value] for ts, value in zip(filled_dates, filled_rows)], index=Index(filled_dates, name="timestamp"), columns=["timestamp", "balance"])        
