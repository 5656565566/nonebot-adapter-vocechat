from typing import Any

from nonebot.adapters import Bot as BaseBot

from .config import BotConfig
from .event import Event
from .message import File, Message, MessageSegment

class Bot(BaseBot):
    def __init__(self, adapter: Any, self_id: str, botConfig: BotConfig) -> None: ...

    async def call_api(self, api: str, **data) -> Any:
        """调用协议 API

        参数:
            api: API 名称
            data: API 参数

        返回:
            API 调用返回数据
        """

    async def handle_event(self, event: Event) -> None: ...
    async def send(
        self, event: Event, message: str | Message | MessageSegment, **kwargs: Any
    ) -> Any: ...
    async def download_file(
        self, file_id: str | None = None, message: Message | MessageSegment | None = None
    ) -> bytes: ...
    async def send_message(
        self,
        message: Message,
        *,
        user_id: int | None = None,
        group_id: int | None = None,
        reply: int | None = None,
        **kwargs: Any
    ) -> Any: ...
    async def upload_file(self, file: File) -> dict[str, Any]: ...
    async def command_add(self, command: str, description: str) -> Any: ...
    async def command_get(self) -> Any: ...
    async def command_delete(self, id: int) -> Any: ...
    async def command_update(self, id: int, command: str, description: str) -> Any: ...
    async def edit(
        self,
        mid: int,
        message: str | Message | MessageSegment,
        properties: dict[str, Any] | None = None,
    ) -> Any: ...
    async def delete(self, mid: int) -> Any: ...
    async def secret_get(self) -> Any: ...
    async def secret_set(self, secret: str) -> Any: ...
    async def user_messages(self, uid: int) -> Any: ...
    async def group_messages(self, gid: int) -> Any: ...