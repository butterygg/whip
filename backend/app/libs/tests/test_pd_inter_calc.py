# pylint: disable=unused-argument
# pylint: disable=redefined-outer-name
import pytest

from ...treasury import actions
from ...treasury.models import ERC20, Treasury


@pytest.mark.asyncio
async def test_single_tranfer_balance_lt_24hrs_after_transfer(
    setup_single_transfer_test,
):
    treasury = Treasury(
        address="0x0",
        assets=[
            ERC20(
                token_name="abc",
                token_symbol="ABC",
                token_address="0xabc",
                balance=1000,
                balance_usd=285.29906,
            ),
        ],
    )

    balances_and_transfers = await actions.make_transfers_balances_for_treasury(
        treasury
    )
    prices = await actions.make_prices_from_tokens({("ABC", "0xabc")})

    balances = await actions.make_balances_from_transfers_and_prices(
        balances_and_transfers, prices
    )
    print(balances)

    abc_price_for_date_of_last_transfer = prices.prices["ABC"]["price"].iloc[-2]
    abc_current_balance = treasury.assets[0].balance
    assert (
        balances.usd_balances["ABC"].iloc[-1]
        == abc_price_for_date_of_last_transfer * abc_current_balance
    )
