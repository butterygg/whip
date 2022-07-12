from datetime import datetime, timedelta

from dateutil.tz import UTC
from dateutil.utils import today as today_in
from httpx import HTTPStatusError, Request, Response


def raise_http_status_error_404(_):
    raise HTTPStatusError(
        "mocked http status error",
        request=Request("get", "http://"),
        response=Response(404),
    )


class MockResponse:
    status_code = None
    text = ""

    def raise_for_status(self):
        pass

    @staticmethod
    def json():
        return None


async def return_mocked_resp(*_, **__):
    return MockResponse()


def mocked_datetime(offset: int = 0, use_today: bool = False):
    _mocked_datetime = datetime(2022, 1, 1) if not use_today else today_in(UTC)
    return _mocked_datetime + timedelta(offset)


covalent_transfers_v2_transfers = [
    {
        "block_signed_at": "2021-08-30T18:26:19Z",
        "block_height": 13128493,
        "tx_hash": "0x97aeaf0160ecf1854aec81ba2d1bd0fb4212edd65d05183a8461a2b9768589ac",
        "tx_offset": 93,
        "successful": True,
        "from_address": "0xcf8db36ebecce3608394fd6031dc7abd2a2ab839",
        "from_address_label": None,
        "to_address": "0xd9107d1d077c2516e83cb41f41883570d904f050",
        "to_address_label": None,
        "value": "0",
        "value_quote": 0.0,
        "gas_offered": 111537,
        "gas_spent": 71210,
        "gas_price": 150000000000,
        "fees_paid": None,
        "gas_quote": 35.83383775085449,
        "gas_quote_rate": 3354.757080078125,
        "transfers": [
            {
                "block_signed_at": "2021-08-30T18:26:19Z",
                "tx_hash": "0x97aeaf0160ecf1854aec81ba2d1bd0fb4212edd65d05183a8461a2b9768589ac",
                "from_address": "0xd9107d1d077c2516e83cb41f41883570d904f050",
                "from_address_label": None,
                "to_address": "0x78605df79524164911c144801f41e9811b7db73d",
                "to_address_label": None,
                "contract_decimals": 18,
                "contract_name": "SushiBar",
                "contract_ticker_symbol": "xSUSHI",
                "contract_address": "0x8798249c2e607446efb7ad49ec89dd1865ff4272",
                "logo_url": "",
                "transfer_type": "IN",
                "delta": "2132233813768734282598109",
                "balance": None,
                "quote_rate": 14.241937637329102,
                "delta_quote": 3.0367141003898706e7,
                "balance_quote": None,
                "method_calls": None,
            }
        ],
    },
    {
        "block_signed_at": "2021-08-24T04:20:02Z",
        "block_height": 13085815,
        "tx_hash": "0x56cece56a7f555aa854983db8cac0ccd0d116f786471478aaba9645b4f18413b",
        "tx_offset": 286,
        "successful": True,
        "from_address": "0x43a330dec81bbd5e21f41c6b8354e54d481efc93",
        "from_address_label": None,
        "to_address": "0x8798249c2e607446efb7ad49ec89dd1865ff4272",
        "to_address_label": None,
        "value": "0",
        "value_quote": 0.0,
        "gas_offered": 77517,
        "gas_spent": 51678,
        "gas_price": 80000000000,
        "fees_paid": None,
        "gas_quote": 13.561120724765624,
        "gas_quote_rate": 3280.19677734375,
        "transfers": [
            {
                "block_signed_at": "2021-08-24T04:20:02Z",
                "tx_hash": "0x56cece56a7f555aa854983db8cac0ccd0d116f786471478aaba9645b4f18413b",
                "from_address": "0x43a330dec81bbd5e21f41c6b8354e54d481efc93",
                "from_address_label": None,
                "to_address": "0x78605df79524164911c144801f41e9811b7db73d",
                "to_address_label": None,
                "contract_decimals": 18,
                "contract_name": "SushiBar",
                "contract_ticker_symbol": "xSUSHI",
                "contract_address": "0x8798249c2e607446efb7ad49ec89dd1865ff4272",
                "logo_url": "",
                "transfer_type": "IN",
                "delta": "1000000000000000000",
                "balance": None,
                "quote_rate": 15.205791473388672,
                "delta_quote": 15.205791473388672,
                "balance_quote": None,
                "method_calls": None,
            }
        ],
    },
]

covalent_portfolio_v2_transfers = [
    {
        "contract_decimals": 18,
        "contract_name": "Ether",
        "contract_ticker_symbol": "ETH",
        "contract_address": "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
        "supports_erc": None,
        "logo_url": "",
        "holdings": [
            {
                "timestamp": "2022-06-30T00:00:00Z",
                "quote_rate": 1027.9667,
                "open": {
                    "balance": "19171059900927579923741",
                    "quote": 1.9707212e7,
                },
                "high": {
                    "balance": "19171059900927579923741",
                    "quote": 1.9707212e7,
                },
                "low": {
                    "balance": "19171059900927579923741",
                    "quote": 1.9707212e7,
                },
                "close": {
                    "balance": "19171059900927579923741",
                    "quote": 1.9707212e7,
                },
            },
            {
                "timestamp": "2022-06-29T00:00:00Z",
                "quote_rate": 1107.7135,
                "open": {
                    "balance": "19171059900927579923741",
                    "quote": 2.1236042e7,
                },
                "high": {
                    "balance": "19171059900927579923741",
                    "quote": 2.1236042e7,
                },
                "low": {
                    "balance": "19171059900927579923741",
                    "quote": 2.1236042e7,
                },
                "close": {
                    "balance": "19171059900927579923741",
                    "quote": 2.1236042e7,
                },
            },
        ],
    }
]

spam_token_transfer = {
    "contract_decimals": 18,
    "contract_name": "MockedSpam",
    "contract_ticker_symbol": "MckSpm",
    "contract_address": "0x7265616c6c795f6261645f6d6f636b65645f7370616d",
    "supports_erc": True,
    "logo_url": "",
    "holdings": [
        {
            "timestamp": "2022-06-30T00:00:00Z",
            "quote_rate": 1027.9667e24,
            "open": {
                "balance": "19171059900927579923741",
                "quote": 1.9707212e27,
            },
            "high": {
                "balance": "19171059900927579923741",
                "quote": 1.9707212e27,
            },
            "low": {
                "balance": "19171059900927579923741",
                "quote": 1.9707212e27,
            },
            "close": {
                "balance": "19171059900927579923741",
                "quote": 1.9707212e27,
            },
        },
        {
            "timestamp": "2022-06-29T00:00:00Z",
            "quote_rate": 1107.7135e24,
            "open": {
                "balance": "19171059900927579923741",
                "quote": 2.1236042e27,
            },
            "high": {
                "balance": "19171059900927579923741",
                "quote": 2.1236042e27,
            },
            "low": {
                "balance": "19171059900927579923741",
                "quote": 2.1236042e27,
            },
            "close": {
                "balance": "19171059900927579923741",
                "quote": 2.1236042e27,
            },
        },
    ],
}
