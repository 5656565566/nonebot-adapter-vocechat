from datetime import datetime
from typing import Any, Literal

from nonebot.adapters import Event as BaseEvent
from nonebot.compat import model_dump
from nonebot.utils import escape_tag
from pydantic import BaseModel, ConfigDict, model_validator
from typing_extensions import override

from .api import ContentType
from .message import File, Message, MessageSegment

class Target(BaseModel):
    gid: int | None = None
    uid: int | None = None

class Event(BaseEvent):
    time: datetime | None = None

    created_at: int
    from_uid: int
    mid: int
    target: Target
    self_uid: str  # 机器人自身用户ID 由适配器注入

    @override
    def get_event_name(self) -> str:
        raise ValueError("Event has no name!")

    @override
    def get_type(self) -> str:
        raise ValueError("Event has no type!")

    @override
    def get_event_description(self) -> str:
        return escape_tag(repr(model_dump(self)))

    @override
    def get_message(self) -> Message:
        raise ValueError("Event has no message!")

    @override
    def get_user_id(self) -> str:
        return str(self.from_uid)
    
    @override
    def get_session_id(self) -> str:
        if self.target.gid:
            return f"gid_{self.target.gid}_uid_{self.from_uid}"
        elif self.target.uid:
            return f"uid_{self.from_uid}"
        return str(self.from_uid)

    @override
    def is_tome(self) -> bool:
        return False

class MessageDetail(BaseModel):
    content: str | None = None
    content_type: ContentType = ContentType.TEXT_PLAIN
    expires_in: int | None = None
    properties: dict[str, Any] | None = None
    type: Literal["reaction", "normal", "reply"] = "normal"

class Reply(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    mid: int
    message: Message | None = None

class MessageEvent(Event):
    """消息事件基类"""

    message_id: int | None = None
    to_me: bool = False
    message: Message | None = None
    original_message: Message | None = None
    reply: Reply | None = None
    detail: MessageDetail

    @override
    def get_type(self) -> str:
        return "message"

    @override
    def get_event_name(self) -> str:
        return "message"

    @override
    def is_tome(self) -> bool:
        return self.to_me

    @override
    def get_message(self) -> Message:
        return self.message or Message()

    @model_validator(mode="after")
    def parse_message_from_detail(self) -> "MessageEvent":
        """根据 detail 自动解析并填充 message 字段"""
        if self.detail.content_type == ContentType.TEXT_PLAIN:
            self.message = Message(MessageSegment.text(self.detail.content or ""))
        elif self.detail.content_type == ContentType.TEXT_MARKDOWN:
            self.message = Message(MessageSegment.markdown(self.detail.content or ""))
        elif self.detail.content_type == ContentType.VOCECHAT_FILE:
            file_type = "file"
            content = self.detail.content or ""
            properties = self.detail.properties or {}

            if isinstance(content, str):
                lowered_content = content.lower()
                if lowered_content.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".avif", ".ico")):
                    file_type = "image"
                elif lowered_content.endswith((".mp4", ".webm", ".mov", ".mkv", ".avi", ".flv", ".wmv", ".m4v")):
                    file_type = "video"

            if properties.get("width") and properties.get("height"):
                file_type = "image"

            if file_type == "image":
                file_seg = MessageSegment.image(file_id=content, properties=properties or None)
            elif file_type == "video":
                file_seg = MessageSegment.video(file_id=content, properties=properties or None)
            else:
                file_seg = MessageSegment.file(file_id=content, properties=properties or None)
            self.message = Message(file_seg)
        elif self.detail.content_type == ContentType.VOCECHAT_AUDIO:
            file_seg = MessageSegment.audio(
                file_id=self.detail.content or "", properties=self.detail.properties or None
            )
            self.message = Message(file_seg)
        elif self.detail.content_type == ContentType.VOCECHAT_ARCHIVE:
            self.message = Message(MessageSegment.archive(archive_id=self.detail.content or ""))
        else:
            self.message = Message(MessageSegment.text(self.detail.content or ""))

        if self.target.uid is not None and self.target.gid is None:
            self.to_me = True

        return self

    @override
    def get_event_description(self) -> str:
        target_type = "Group" if self.target.gid else "Private"
        target_id = self.target.gid or self.target.uid
        if target_type == "Private":
            return escape_tag(
                f"Message {self.mid} from: {self.from_uid}: " f"{self.get_message()}"
            )

        return escape_tag(
            f"Message {self.mid} from: {self.from_uid}@[群:{target_id}]: "
            f"{self.get_message()}"
        )


class PrivateMessageEvent(MessageEvent):
    """私聊消息事件"""

    @override
    def get_event_name(self) -> str:
        return "message.private"


class GroupMessageEvent(MessageEvent):
    """群聊消息事件"""

    @override
    def get_event_name(self) -> str:
        return "message.group"

