from typing import Any, Dict, Optional, Literal
from typing_extensions import override

from nonebot.utils import escape_tag
from nonebot.compat import model_dump
from nonebot.adapters import Event as BaseEvent
from pydantic import BaseModel, model_validator
from datetime import datetime

from .message import Message, MessageSegment
from .api import ContentType

class Target(BaseModel):
    gid: Optional[int] = None
    uid: Optional[int] = None

class Event(BaseEvent):
    time: Optional[datetime] = None

    created_at: int
    from_uid: int
    mid: int
    target: Target
    self_uid: str  # 机器人自身用户ID，由适配器注入

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
    content: Optional[str] = None
    content_type: ContentType = ContentType.TEXT_PLAIN
    expires_in: Optional[int] = None
    properties: Optional[Dict[str, Any]] = None
    type: Literal["reaction", "normal", "reply"] = "normal"

class Reply(BaseModel):
    mid: int
    message: Optional[Message] = None

class ReactionDetail(BaseModel):
    detail: Dict[str, Any]
    mid: int
    type: str

class MessageEvent(Event):
    """消息事件基类"""
    message_id: Optional[int] = None
    to_me: bool = False
    message: Optional[Message] = None
    original_message: Optional[Message] = None
    reply: Optional[Reply] = None

    @override
    def get_type(self) -> str:
        return "message"
    
    @override
    def get_event_name(self) -> str:
        return "message"

    @override
    def is_tome(self) -> bool:
        # 私聊消息直接判断目标是否是机器人
        return self.to_me
    
    @override
    def get_event_description(self) -> str:
        target_type = "Group" if self.target.gid else "Private"
        target_id = self.target.gid or self.target.uid
        if target_type == "Private":
            return escape_tag(
                f"Message {self.mid} from: {self.from_uid}: "
                f"{self.get_message()}"
            )
        
        return escape_tag(
                f"Message {self.mid} from: {self.from_uid}@[群:{target_id}]: "
                f"{self.get_message()}"
            )
    

class MessageNewEvent(MessageEvent):
    """新消息事件"""
    detail: MessageDetail
    
    @override
    def get_event_name(self) -> str:
        return "message.new"
    
    @override
    def get_message(self) -> Message:
        return self.message or Message()
    
    @model_validator(mode="after")
    def parse_message_from_detail(self) -> "MessageNewEvent":
        """根据 detail 自动解析并填充 message 字段"""
        if self.detail.content_type == "text/plain":
            self.message = Message(MessageSegment.text(self.detail.content or ""))
        elif self.detail.content_type == "text/markdown":
            self.message = Message(MessageSegment.markdown(self.detail.content or ""))
        elif self.detail.content_type == "vocechat/file":
            file_seg = MessageSegment.file(file_id=self.detail.content or "")
            if self.detail.properties:
                file_seg.data["properties"] = self.detail.properties
            self.message = Message(file_seg)
        else:
            self.message = Message(MessageSegment.text(self.detail.content or ""))
        return self

class NoticeEvent(Event):
    """通知事件"""
    @override
    def get_type(self) -> str:
        return "notice"

class MessageEditEvent(NoticeEvent):
    """消息编辑事件"""
    detail: ReactionDetail

    @override
    def get_event_name(self) -> str:
        return "notice.message.edit"

    @override
    def get_message(self) -> Message:
        return self.message

    @model_validator(mode="after")
    def parse_message_from_detail(self) -> "MessageEditEvent":
        """根据 detail 自动解析并填充 message 字段"""
        content = self.detail.detail.get("content", "")  # type: ignore
        content_type = self.detail.detail.get("content_type", "text/plain")  # type: ignore
        properties = self.detail.detail.get("properties")  # type: ignore

        if content_type == "text/plain":
            self.message = Message(MessageSegment.text(content))
        elif content_type == "text/markdown":
            self.message = Message(MessageSegment.markdown(content))
        elif content_type == "vocechat/file":
            file_seg = MessageSegment.file(file_id=content)
            if properties:
                file_seg.data["properties"] = properties
            self.message = Message(file_seg)
        else:
            self.message = Message(MessageSegment.text(content))
        return self


class MessageDeleteEvent(NoticeEvent):
    """消息删除事件"""
    detail: ReactionDetail
    
    @override
    def get_event_name(self) -> str:
        return "notice.message.delete"
    
    @property
    def deleted_mid(self) -> int:
        """被删除的消息ID"""
        return self.detail.mid

class FileMessageEvent(MessageNewEvent):
    """文件消息事件"""
    
    @override
    def get_event_name(self) -> str:
        return "message.file"
    
    @property
    def file_path(self) -> str:
        """文件路径"""
        return self.detail.content or ""  # type: ignore
    
    @property
    def file_name(self) -> str:
        """文件名"""
        if self.detail.properties:
            return self.detail.properties.get("name", "")  # type: ignore
        return ""
    
    @property
    def file_size(self) -> int:
        """文件大小"""
        if self.detail.properties:
            return self.detail.properties.get("size", 0)  # type: ignore
        return 0
    
    @property
    def file_type(self) -> str:
        """文件MIME类型"""
        if self.detail.properties:
            return self.detail.properties.get("content_type", "")  # type: ignore
        return ""
    
    @override
    def get_message(self) -> Message:
        # 文件消息特殊处理
        file_seg = MessageSegment.file(file_id= self.detail.content or "")
        # 添加文件元数据
        if self.detail.properties:
            file_seg.data["properties"] = self.detail.properties
        return Message(file_seg)