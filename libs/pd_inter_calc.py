from datetime import datetime, timedelta
from dateutil.utils import today
from dateutil.tz import UTC

from pandas import Index, Series

def portfolio_filler(portfolio_balances: Series, quote_rates: Series) -> Series:
    filled_rows = []
    filled_dates = []
    rows = list(portfolio_balances.to_dict().items())
    index = 0
    for date, balance in rows:
        curr_date: datetime = date[0]
        next_date: datetime = rows[index + 1][0][0]

        curr_balance = balance
        while curr_date < next_date:
            curr_quote = quote_rates.loc[curr_date.strftime("%Y-%m-%d")]
            filled_rows.append(curr_balance * curr_quote)
            filled_dates.append(curr_date)

            curr_date += timedelta(days=1)

        index += 1
        if index == len(rows) - 1:
            curr_date = today(UTC)
            prev_date: datetime = filled_dates[-1]
            prev_date += timedelta(days=1)
            sub_cnt = 0
            while prev_date < curr_date:
                    
                curr_quote = quote_rates.loc[prev_date.strftime("%Y-%m-%d")]
                filled_rows.append(curr_balance * curr_quote)
                filled_dates.append(prev_date)

                prev_date += timedelta(days=1)
                sub_cnt += 1
            break

    return Series(filled_rows, index=Index(filled_dates, name="timestamp"), name="balance")        
