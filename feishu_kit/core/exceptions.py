"""Custom exception hierarchy for feishu-kit."""


class FeishuKitError(Exception):
    """Base exception for all feishu-kit errors."""


class AuthenticationError(FeishuKitError):
    """Raised when Feishu authentication fails (invalid app_id/app_secret)."""


class RateLimitError(FeishuKitError):
    """Raised when Feishu API rate limit is exceeded."""

    def __init__(self, retry_after: int | None = None) -> None:
        self.retry_after = retry_after
        msg = "Rate limit exceeded"
        if retry_after:
            msg += f" (retry after {retry_after}s)"
        super().__init__(msg)


class APIError(FeishuKitError):
    """Raised when a Feishu API call returns a non-zero code."""

    def __init__(self, code: int, msg: str) -> None:
        self.code = code
        self.msg = msg
        super().__init__(f"API error {code}: {msg}")
