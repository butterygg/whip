# Setup

## How to run a script

First, make sure your docker compose is up (we need the Redis instance running).

Then, in a shell:

- cd in the `backend` folder
- make sure the `.env` file is loaded in your shell environment
- run with, eg, `REDIS_URL=redis://localhost:6379 python -m scripts.volacsv …`

# Scripts

## volacsv

This will output a CSV with 7day std dev ("volatility") of USD quotation, for assets of a given
portfolio.

By default, (start, end) dates are (1y ago - 1d, yesteraday).

Example usage:

```sh
REDIS_URL=redis://localhost:6379 python -m scripts.volacsv 0x567d220b0169836cbf351df70a9c517096ec9de7 > primedao-$(date +'%Y-%m-%d').csv
```

You can define start and end dates as well:

```sh
REDIS_URL=redis://localhost:6379 python -m scripts.volacsv 0x567d220b0169836cbf351df70a9c517096ec9de7 2022-01-01 2022-04-01 > primedao-2022-01-01-2022-04-01.csv
```
