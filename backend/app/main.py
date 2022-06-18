import datetime
from dataclasses import asdict, dataclass
from typing import Iterable, Literal, TypeVar, Union

import dateutil
from fastapi import FastAPI
from pytz import UTC

from .libs.tasks import get_assets
from .libs.types import Treasury

app = FastAPI()

T = TypeVar("T")


def snake_to_camel_dict_factory(items: Iterable[tuple[str, T]]) -> dict[str, T]:
    def camel(snake_str):
        components = snake_str.split("_")
        return components[0] + "".join(x.title() for x in components[1:])

    return {camel(k): v for k, v in items}


@dataclass
class PortfolioAsset:
    allocation: float
    volatility: float
    risk_contribution: float


@dataclass
class PortfolioKpis:
    total_value: float
    volatility: float
    return_vs_market: Union[float, Literal["Infinity"]]


@dataclass
class Portfolio:
    assets: dict[str, PortfolioAsset]
    kpis: PortfolioKpis
    data: dict[str, float]

    @classmethod
    def from_treasury_with_assets(
        cls,
        treasury: Treasury,
        augmented_token_hist_prices,
        asset_hist_balances,  # pylint: disable=unused-argument
        augmented_total_balance,
        start: str,
        end: str,
    ):
        histprices = {
            symbol: athp.set_index("timestamp").loc[start:end]
            for symbol, athp in augmented_token_hist_prices.items()
        }
        totalbalance = augmented_total_balance.loc[start:end]

        assets = {
            a.token_symbol: PortfolioAsset(
                allocation=a.balance / treasury.usd_total,
                volatility=histprices[a.token_symbol]["std_dev"].mean(),
                risk_contribution=a.risk_contribution,
            )
            for a in treasury.assets
        }

        if (start not in totalbalance.index) or (totalbalance.loc[start].balance == 0):
            market_return = "Infinity"
        else:
            eth_series = histprices["ETH"]
            market_return = (
                totalbalance.loc[end].balance - totalbalance.loc[start].balance
            ) / totalbalance.loc[start].balance - (
                eth_series.loc[end].price - eth_series.loc[start].price
            ) / eth_series.loc[
                start
            ].price

        kpis = PortfolioKpis(
            total_value=treasury.usd_total,
            volatility=totalbalance.std_dev.mean(),
            return_vs_market=market_return,
        )

        data = {
            timestamp.to_pydatetime().strftime("%Y-%m-%d"): balance
            for timestamp, balance in totalbalance.to_dict()["balance"].items()
        }
        return cls(assets=assets, kpis=kpis, data=data)


@app.get("/portfolio/{address}/{start}")
async def get_portfolio(address: str, start=str):
    end_date = dateutil.utils.today(UTC) - datetime.timedelta(days=1)
    end = end_date.strftime("%Y-%m-%d")

    portfolio = Portfolio.from_treasury_with_assets(
        *(await get_assets.build_treasury_with_assets(address, 1, start, end)),
        start,
        end,
    )

    return asdict(
        portfolio,
        dict_factory=snake_to_camel_dict_factory,
    )


@app.get("/backtest/spread/{address}/{start}/{percentage}")
async def backtest_spread(address: str, start: str, percentage: int):
    assert 0 <= percentage <= 100

    end_date = dateutil.utils.today(UTC) - datetime.timedelta(days=1)
    end = end_date.strftime("%Y-%m-%d")

    portfolio = Portfolio.from_treasury_with_assets(
        *(
            await get_assets.build_spread_treasury_with_assets(
                address,
                1,
                start,
                end,
                spread_token_name="USD Coin",
                spread_token_symbol="USDC",
                spread_token_address="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
                spread_percentage=percentage,
            )
        ),
        start,
        end,
    )

    return asdict(
        portfolio,
        dict_factory=snake_to_camel_dict_factory,
    )
