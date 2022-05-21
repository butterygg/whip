# Calculations

## Measuring Volatility

Volatility of an asset is measured as the seven day standard deviation of the rate of returns for an asset.

The rate of return is how much profit the treasury accrues for holding a given asset in its wallet. In the context of cryptocurrencies, the assets a treasury holds can often be quite volatile. To measure this volatility, a seven day rolling standard deviation is calculated for each of the assets based on their rate of returns for that period.

```
rate of returns = price of an asset next day / price of an asset the previous day

ln(rate of returns)
```

Standard deviation measures how volatile a value in a dataset is from it's mean. If you think of the mean as being a point where the price of an assset is stabilised/predictable then the standard deviation measures how unstable/unpredictable an asset value is.

A seven day rolling calculation for an asset's standard deviation allows us to continually asses the volatility of an asset over time as external market factors affect it's price.

The historical prices for the assets were obtained using Covalent's [historical prices endpoint](https://www.covalenthq.com/docs/api/#/0/Get%20historical%20token%20prices/USD/1). A timeseries of this historical price data was then constructed as a pandas Dateframe, where the returns and standard deviation of the asset was also calculated and made into additional features of this dataset.

## Historical Balances

The historical balances of treasuries are calculated over a period of time ranging between ther time when the asset was first transfered to a given treasury to the current date.

The transactions for these transfers for ERC20 tokens were obtained from Covalent's [transfers endpoints](https://www.covalenthq.com/docs/api/#/0/Get%20ERC20%20token%20transfers%20for%20address/USD/1) were used to obtian the USD value of the assets.

The historical balances for the treasury is updated based on the whether or not the transfer was an inflow or outflow as described in the endpoints response object

```python
if transfer["transfer_type"] == "IN":
    curr_balance += delta / 10 ** decimals if decimals > 0 else 1
    balances.append(curr_balance)
else:
    curr_balance -= delta / 10 ** decimals if decimals > 0 else 1
    balances.append(curr_balance)
```

where the `delta` is how much of the ERC20 tokens are received or sent, `decimals` is also described in the response object and used to properly decribe the token balance as a fixed point number.

The historical quote rates for each asset was then used to produce a dataset describing the historical value of a treasury's balance for that asset. **That is, for each day between transfers, the product of the quote rate for the asset and the asset balance for a treasury was calculated and recorded on a timeseries dataset.**
