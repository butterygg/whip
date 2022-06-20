from json import loads
from logging import Logger

from celery.utils import log
from httpx import AsyncClient, HTTPStatusError, Request, Response
from pytest import MonkeyPatch, mark

from backend.app.libs.tokenlists import get_token_list, maybe_populate_whitelist


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


class MockAsyncClient:
    def get(self, _):
        return MockResponse()


class TestTokenList:
    log_resp = ""

    async def mock_get_uniswap(self, _: str):
        return MockResponse()

    @mark.asyncio
    async def test_get_token_list_success(self, monkeypatch: MonkeyPatch):
        monkeypatch.setattr(log, "get_task_logger", Logger("mock_task_logger"))

        monkeypatch.setattr(AsyncClient, "get", self.mock_get_uniswap)
        monkeypatch.setattr(
            "backend.app.libs.tokenlists.store_token_whitelist",
            lambda x: None,
            raising=True,
        )
        await get_token_list("https://tokens.coingecko.com/uniswap/all.json")
        assert True

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
        def mock_error_log(_, error_str: str, arg):
            self.log_resp = error_str.replace("%s", arg)

        async def async_return(*_):
            return MockResponse()

        monkeypatch.setattr(Logger, "error", mock_error_log, raising=True)

        url = "https://tokens.coingecko.com/uniswap/all.json"
        monkeypatch.setattr(AsyncClient, "get", async_return)
        monkeypatch.setattr(MockResponse, "json", json_resp)
        await get_token_list(url)

        assert (
            self.log_resp == f"the token list url given is likely not supported: {url}"
        )

    @mark.asyncio
    async def test_maybe_populate_whitelist_success(self, monkeypatch: MonkeyPatch):
        monkeypatch.setattr(
            "backend.app.libs.tokenlists.retrieve_token_whitelist",
            lambda: ["0x6d6f636b5f746f6b656e5f31", "0x6d6f636b5f746f6b656e5f32"],
            raising=True,
        )
        mocked_whitelist = await maybe_populate_whitelist()
        assert len(mocked_whitelist) == 2
        assert "0x6d6f636b5f746f6b656e5f31" in mocked_whitelist
        assert "0x6d6f636b5f746f6b656e5f32" in mocked_whitelist

    @mark.asyncio
    async def test_get_token_list_resp_err_404(self, monkeypatch: MonkeyPatch):
        def mock_warn_log(_, error_str: str, arg):
            self.log_resp = error_str.replace("%s", arg)

        def raise_http_status_error(_):
            raise HTTPStatusError(
                "mocked http status error",
                request=Request("get", "http://"),
                response=Response(404),
            )

        monkeypatch.setattr(log, "get_task_logger", Logger("mock_task_logger"))
        monkeypatch.setattr(Logger, "warn", mock_warn_log, raising=True)

        monkeypatch.setattr(AsyncClient, "get", self.mock_get_uniswap)
        monkeypatch.setattr(MockResponse, "status_code", 404)
        monkeypatch.setattr(MockResponse, "raise_for_status", raise_http_status_error)

        url = "https://tokens.coingecko.com/uniswap/all.json"
        await get_token_list(url)

        assert self.log_resp == f"404 response for {url}, aborting..."

    @mark.asyncio
    async def test_get_token_list_resp_err_5xx(self, monkeypatch: MonkeyPatch):
        def mock_error_log(_, error_str: str, arg):
            self.log_resp = error_str.replace("%s", arg)

        def raise_http_status_error(_):
            raise HTTPStatusError(
                "mocked http status error",
                request=Request("get", "http://"),
                response=Response(501),
            )

        async def mock_retry(*_):
            pass

        monkeypatch.setattr(log, "get_task_logger", Logger("mock_task_logger"))
        monkeypatch.setattr(Logger, "error", mock_error_log, raising=True)

        monkeypatch.setattr(AsyncClient, "get", self.mock_get_uniswap)
        monkeypatch.setattr(MockResponse, "status_code", 501)
        monkeypatch.setattr(MockResponse, "raise_for_status", raise_http_status_error)
        monkeypatch.setattr(
            "backend.app.libs.tokenlists.store_token_whitelist",
            lambda _: None,
            raising=True,
        )
        monkeypatch.setattr(
            "backend.app.libs.tokenlists.retry",
            mock_retry,
            raising=True,
        )

        url = "https://tokens.coingecko.com/uniswap/all.json"
        await get_token_list(url)

        assert self.log_resp == f"error receiving token list for {url}, retrying..."

    @mark.asyncio
    async def test_get_token_list_json_err(self, monkeypatch: MonkeyPatch):
        def mock_error_log(_, error_str: str, arg):
            self.log_resp = error_str.replace("%s", arg)

        monkeypatch.setattr(log, "get_task_logger", Logger("mock_task_logger"))
        monkeypatch.setattr(Logger, "error", mock_error_log, raising=True)

        monkeypatch.setattr(AsyncClient, "get", self.mock_get_uniswap)
        monkeypatch.setattr(MockResponse, "json", lambda _: loads("bad json response"))

        url = "https://tokens.coingecko.com/uniswap/all.json"
        await get_token_list(url)

        error_str = (
            f"unable to decode response from {url}"
            + "\n please ensure that `resp.data` is a json formatted string"
        )
        assert self.log_resp == error_str
