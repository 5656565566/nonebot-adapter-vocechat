from typing import Any, Optional

from nonebot.drivers import Response
from nonebot.exception import AdapterException
from nonebot.exception import ActionFailed as BaseActionFailed
from nonebot.exception import ApiNotAvailable as BaseApiNotAvailable
from nonebot.exception import NetworkError as BaseNetworkError


class VoceChatAdapterException(AdapterException):
    def __init__(self) -> None:
        super().__init__("VoceChat")


class NetworkError(BaseNetworkError, VoceChatAdapterException):
    def __init__(self, msg: Optional[str] = None) -> None:
        BaseNetworkError.__init__(self, "VoceChat")
        self.msg: Optional[str] = msg
        """错误原因"""

    def __repr__(self) -> str:
        return f"<NetworkError message={self.msg}>"

    def __str__(self) -> str:
        return self.__repr__()


class ActionFailed(BaseActionFailed, VoceChatAdapterException):
    def __init__(self, response: Response) -> None:
        super().__init__()
        self.status_code: int = response.status_code
        self.headers = response.headers
        self.content = response.content
        self.response = response

        self.code: Optional[int] = None
        self.message: Optional[str] = None
        self.data: Optional[Any] = None

        parsed = self._parse_response(response)
        if parsed:
            self.code = parsed.get("code")
            self.message = parsed.get("message") or parsed.get("msg")
            self.data = parsed.get("data")

    @staticmethod
    def _parse_response(response: Response) -> Optional[dict[str, Any]]:
        content = response.content
        if content is None:
            return None

        if isinstance(content, bytes):
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                return None
        else:
            text = str(content)

        text = text.strip()
        if not text:
            return None

        try:
            import json

            data = json.loads(text)
        except Exception:
            return None

        return data if isinstance(data, dict) else None

    def __repr__(self) -> str:
        return (
            f"<ActionFailed status_code={self.status_code} code={self.code} "
            f"message={self.message}>"
        )

    def __str__(self) -> str:
        return self.__repr__()


class UnauthorizedException(ActionFailed):
    pass


class ForbiddenException(ActionFailed):
    pass


class NotFoundException(ActionFailed):
    pass


class RateLimitException(ActionFailed):
    pass


class ServerError(ActionFailed):
    pass


class ApiNotAvailable(BaseApiNotAvailable, VoceChatAdapterException):
    def __init__(self) -> None:
        BaseApiNotAvailable.__init__(self, "VoceChat")
