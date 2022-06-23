from json import loads
from json.decoder import JSONDecodeError

from httpx import AsyncClient, HTTPStatusError, Request, Response
from pytest import MonkeyPatch, mark, raises

from backend.app.libs.tokenlists import (
    get_token_list,
    maybe_populate_whitelist,
    store_and_get_whitelists,
)


class MockResponse:
    status_code = None

    def raise_for_status(self):
        return None

    @staticmethod
    def json():
        return {
            "name": "MockGecko",
            "logoURI": "https://www.mockgecko.com/mock/path/thumb.jpg",
            "keywords": ["mockfi"],
            "timestamp": "2022-06-19T11:08:16.098+00:00",
            "tokens": [
                {"chainId": 1, "address": "0x6d6f636b5f31"},
                {"chainId": 1, "address": "0x6d6f636b5f32"},
            ],
        }


class TestTokenList:
    async def mock_get_uniswap(self, _: str):
        return MockResponse()

    @mark.asyncio
    async def test_get_token_list_success(self, monkeypatch: MonkeyPatch):
        monkeypatch.setattr(AsyncClient, "get", self.mock_get_uniswap)

        db_payload = {}
        monkeypatch.setattr(
            "backend.app.libs.tokenlists.db.sadd",
            lambda key, *payload: db_payload.update({key: set(payload)}),
            raising=True,
        )

        await store_and_get_whitelists()
        assert db_payload["whitelist"]
        assert len(db_payload["whitelist"]) == 2
        assert "0x6d6f636b5f31" in db_payload["whitelist"]
        assert "0x6d6f636b5f32" in db_payload["whitelist"]

    @mark.asyncio
    @mark.parametrize(
        "json_resp",
        [
            lambda _: {
                "name": "MockGecko",
                "logoURI": "https://www.mockgecko.com/mock/path/thumb.jpg",
                "keywords": ["mockfi"],
                "timestamp": "2022-06-19T11:08:16.098+00:00",
                "tokens": [
                    {"chainId": 1, "address": "0x6d6f636b5f31"},
                    {"chainId": 1},
                ],
            },
            lambda _: {
                "name": "MockGecko",
                "logoURI": "https://www.mockgecko.com/mock/path/thumb.jpg",
                "keywords": ["mockfi"],
                "timestamp": "2022-06-19T11:08:16.098+00:00",
                "tokens": [
                    {"address": "0x6d6f636b5f31"},
                    {"chainId": 1, "address": "0x6d6f636b5f32"},
                ],
            },
            lambda _: {
                "name": "MockGecko",
                "logoURI": "https://www.mockgecko.com/mock/path/thumb.jpg",
                "keywords": ["mockfi"],
                "timestamp": "2022-06-19T11:08:16.098+00:00",
                "toekns": [
                    {"chainId": 1, "address": "0x6d6f636b5f31"},
                    {"chainId": 1, "address": "0x6d6f636b5f32"},
                ],
            },
        ],
    )
    async def test_get_token_list_bad_resp_json(
        self, monkeypatch: MonkeyPatch, json_resp
    ):
        async def async_return(*_):
            return MockResponse()

        url = "https://tokens.coingecko.com/uniswap/all.json"
        monkeypatch.setattr(AsyncClient, "get", async_return)
        monkeypatch.setattr(MockResponse, "json", json_resp)
        with raises(KeyError):
            await get_token_list(url)

    @mark.asyncio
    async def test_maybe_populate_whitelist_success_preprop(
        self, monkeypatch: MonkeyPatch
    ):
        monkeypatch.setattr(
            "backend.app.libs.tokenlists.retrieve_token_whitelist",
            lambda _: ["0x6d6f636b5f746f6b656e5f31", "0x6d6f636b5f746f6b656e5f32"],
            raising=True,
        )
        mocked_whitelist = await maybe_populate_whitelist()
        assert len(mocked_whitelist) == 2
        assert "0x6d6f636b5f746f6b656e5f31" in mocked_whitelist
        assert "0x6d6f636b5f746f6b656e5f32" in mocked_whitelist

    @mark.asyncio
    async def test_get_token_list_resp_err_404(self, monkeypatch: MonkeyPatch):
        def raise_http_status_error(_):
            raise HTTPStatusError(
                "mocked http status error",
                request=Request("get", "http://"),
                response=Response(404),
            )

        monkeypatch.setattr(AsyncClient, "get", self.mock_get_uniswap)
        monkeypatch.setattr(MockResponse, "status_code", 404)
        monkeypatch.setattr(MockResponse, "raise_for_status", raise_http_status_error)

        url = "https://tokens.coingecko.com/uniswap/all.json"
        with raises(HTTPStatusError) as error:
            await get_token_list(url)

            assert "mocked http status error" in str(error.value)

    @mark.asyncio
    async def test_get_token_list_resp_err_5xx(self, monkeypatch: MonkeyPatch):
        def raise_http_status_error(_):
            raise HTTPStatusError(
                "mocked http status error",
                request=Request("get", "http://"),
                response=Response(501),
            )

        monkeypatch.setattr(AsyncClient, "get", self.mock_get_uniswap)
        monkeypatch.setattr(MockResponse, "status_code", 501)
        monkeypatch.setattr(MockResponse, "raise_for_status", raise_http_status_error)

        url = "https://tokens.coingecko.com/uniswap/all.json"
        with raises(HTTPStatusError) as error:
            await get_token_list(url)

            assert "mocked http status error" in str(error.value)

    @mark.asyncio
    async def test_get_token_list_json_err(self, monkeypatch: MonkeyPatch):
        monkeypatch.setattr(AsyncClient, "get", self.mock_get_uniswap)
        monkeypatch.setattr(MockResponse, "json", lambda _: loads("bad json response"))

        url = "https://tokens.coingecko.com/uniswap/all.json"
        with raises(JSONDecodeError):
            await get_token_list(url)
