from src.exceptions import ServerError


class HTTPClientError(ServerError):
    code = 'http_client_error'
    message = 'External HTTP request failed'

    def __init__(
        self,
        message: str | None = None,
        *,
        status_code: int | None = None,
        payload: str | None = None,
        code: str | None = None,
    ):
        super().__init__(message, code=code)
        self.status_code = status_code
        self.payload = payload


class HTTPClientTimeout(HTTPClientError):
    code = 'http_client_timeout'
    message = 'External HTTP request timed out'
