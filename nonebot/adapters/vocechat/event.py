from typing import Any, Dict, Optional
from typing_extensions import override

from nonebot.utils import escape_tag
from nonebot.compat import model_dump
from nonebot.adapters import Event as BaseEvent
from pydantic import BaseModel, Field

from .message import Message, MessageSegment
from .api import ContentType

class Event(BaseEvent):
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
        raise ValueError("Event has no context!")

    @override
    def get_session_id(self) -> str:
        raise ValueError("Event has no context!")

    @override
    def is_tome(self) -> bool:
        return False

class Target(BaseModel):
    gid: Optional[int] = None
    uid: Optional[int] = None

class MessageDetail(BaseModel):
    content: Optional[str] = None
    content_type: ContentType = ContentType.TEXT_PLAIN
    expires_in: Optional[int] = None
    properties: Optional[Dict[str, Any]] = None
    type: str = "normal"

class ReactionDetail(BaseModel):
    detail: Dict[str, Any]
    mid: int
    type: str

class MessageEvent(Event):
    """消息事件基类"""
    created_at: int
    from_uid: int
    mid: int
    target: Target
    self_uid: str  # 机器人自身用户ID，由适配器注入

    @override
    def get_type(self) -> str:
        return "message"
    
    @override
    def get_event_name(self) -> str:
        return "message"
    
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

        # 私聊消息直接判断目标是否是机器人
        if self.target.uid and self.target.uid == int(self.self_uid):
            return True
        
        # 群聊消息检查是否 @机器人
        if hasattr(self, "detail") and getattr(self.detail, "properties", None):  # type: ignore
            mentions = self.detail.properties.get("mentions", [])  # type: ignore
            if mentions and int(self.self_uid) in mentions:
                return True
        
        return False

class MessageNewEvent(MessageEvent):
    """新消息事件"""
    detail: MessageDetail
    
    @override
    def get_event_name(self) -> str:
        return "message.new"
    
    @override
    def get_message(self) -> Message:
        # 根据消息类型创建不同的消息段
        if self.detail.content_type == "text/plain":
            return Message(MessageSegment.text(self.detail.content or ""))
        elif self.detail.content_type == "text/markdown":
            return Message(MessageSegment.markdown(self.detail.content or ""))
        elif self.detail.content_type == "vocechat/file":
            # 文件消息需要特殊处理
            file_seg = MessageSegment.file(file_id= self.detail.content or "")
            # 添加文件元数据
            if self.detail.properties:
                file_seg.data["properties"] = self.detail.properties
            return Message(file_seg)
        return Message(MessageSegment.text(self.detail.content or ""))

class MessageEditEvent(MessageEvent):
    """消息编辑事件"""
    detail: ReactionDetail
    
    @override
    def get_event_name(self) -> str:
        return "message.edit"
    
    @override
    def get_message(self) -> Message:
        # 编辑后的消息内容
        content = self.detail.detail.get("content", "")  # type: ignore
        
        # 获取消息类型，默认为文本
        content_type = self.detail.detail.get("content_type", "text/plain")  # type: ignore
        
        # 根据消息类型创建消息段
        if content_type == "text/plain":
            return Message(MessageSegment.text(content))
        elif content_type == "text/markdown":
            return Message(MessageSegment.markdown(content))
        elif content_type == "vocechat/file":
            file_seg = MessageSegment.file(file_id= content)
            # 添加文件元数据
            properties = self.detail.detail.get("properties")  # type: ignore
            if properties:
                file_seg.data["properties"] = properties
            return Message(file_seg)
        return Message(MessageSegment.text(content))

class MessageDeleteEvent(MessageEvent):
    """消息删除事件"""
    detail: ReactionDetail
    
    @override
    def get_event_name(self) -> str:
        return "message.delete"
    
    @property
    def deleted_mid(self) -> int:
        """被删除的消息ID"""
        return self.detail.mid

class MessageReplyEvent(MessageEvent):
    """消息回复事件"""
    detail: MessageDetail = Field(..., alias="detail")
    reply_to_mid: int
    
    @override
    def get_event_name(self) -> str:
        return "message.reply"
    
    @override
    def get_message(self) -> Message:
        # 创建回复消息内容
        if self.detail.content_type == "text/plain":
            return Message(MessageSegment.text(self.detail.content or ""))
        elif self.detail.content_type == "text/markdown":
            return Message(MessageSegment.markdown(self.detail.content or ""))
        elif self.detail.content_type == "vocechat/file":
            file_seg = MessageSegment.file(file_id= self.detail.content or "")
            if self.detail.properties:
                file_seg.data["properties"] = self.detail.properties
            return Message(file_seg)
        return Message(MessageSegment.text(self.detail.content or ""))
    
    @property
    def reply_message_id(self) -> int:
        """被回复的消息ID"""
        return self.reply_to_mid

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