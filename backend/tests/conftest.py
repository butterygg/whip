from httpx import HTTPStatusError, Request, Response


class MockProvider:
    db_payload = {}

    def sadd(self, key: str, *payload):
        self.db_payload.update({key: set(payload)})

    def smembers(self, _):
        return self.db_payload


def raise_http_status_error_404(_):
    raise HTTPStatusError(
        "mocked http status error",
        request=Request("get", "http://"),
        response=Response(404),
    )


def raise_http_status_error_501(_):
    raise HTTPStatusError(
        "mocked http status error",
        request=Request("get", "http://"),
        response=Response(501),
    )
