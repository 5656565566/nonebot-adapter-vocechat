from typing import Any, Dict

from nonebot.adapters import Bot as BaseBot

from .event import Event, MessageEvent
from .message import Message, MessageSegment, File

class Bot(BaseBot):
    async def call_api(self, api: str, **data) -> Any:
        """调用 OneBot 协议 API。

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
        event: MessageEvent | Event | None = None,
        **kwargs: Any,
    ) -> Any: ...
    async def upload_file(self, file: File) -> Dict[str, Any]: ...
    async def command_add(self, command: str, description: str) -> None: ...
    async def command_get(self) -> None: ...
    async def command_delete(self, id: int) -> None: ...
    async def command_update(self, id: int, command: str, description: str) -> None: ...