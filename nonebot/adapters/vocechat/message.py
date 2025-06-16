from typing import Type, Iterable, Union, Dict, List, Any, Optional
from typing_extensions import override

from nonebot.adapters import Message as BaseMessage
from nonebot.adapters import MessageSegment as BaseMessageSegment
from nonebot.drivers import URL
from pathlib import Path

import httpx

from .api import ContentType

class File:
    """文件类 方便处理文件"""
    def __init__(
        self,
        path: Optional[Path] = None,
        data: Optional[bytes] = None,
        file_id: Optional[str] = None,
        url: Optional[URL] = None,
        filename: Optional[str] = None,
    ) -> None:
        if path is None and data is None and file_id is None and url is None:
            raise ValueError("Either 'path' 'data' 'file_id' 'url' must be provided")
        
        self._path = path
        self._data = data
        self._url = url
        self.file_id = file_id
        self.filename = filename

    async def get_data(self) -> bytes:
        if self._data is not None:
            return self._data
        if self._path is not None:
            with open(self._path, "rb") as f:
                return f.read()
        if self._url is not None:
            async with httpx.AsyncClient() as client:
                response = await client.get(self._url)
                return response.content
        
        raise ValueError("No valid data source provided")

    def __str__(self):
        return self.filename or self.file_id or "Unknown"

class MessageSegment(BaseMessageSegment["Message"]):
    @classmethod
    @override
    def get_message_class(cls) -> Type["Message"]:
        return Message

    @override
    def __str__(self) -> str:
        if self.is_text():
            return self.data.get("text", "")
        elif self.type == "markdown":
            return "[Markdown]"
        elif self.type == "file":
            return f"[File: {self.data.get('file', '')}]"
        return ""
    
    @override
    def is_text(self) -> bool:
        return self.type == "text"
    
    @staticmethod
    def text(text: str) -> "MessageSegment":
        """创建文本消息段"""
        return MessageSegment("text", {"text": text})
    
    @staticmethod
    def markdown(md: str) -> "MessageSegment":
        """创建Markdown消息段"""
        return MessageSegment("markdown", {"text": md})

    @staticmethod
    def file(data: Union[str, bytes, Path]= None, filename: Optional[str] = None, file_id: Optional[str] = None) -> "MessageSegment":
        """创建文件消息段"""
        if isinstance(data, str) and (data.startswith("http://") or data.startswith("https://")):
            data = Path(url= URL(data))
        elif isinstance(data, str):
            data = Path(data)
        
        if isinstance(data, Path):
            file_obj = File(path=data, filename=filename or data.name)
        elif isinstance(data, bytes):
            file_obj = File(data=data, filename=filename)
        elif isinstance(data, URL):
            file_obj = File(url=data, filename=filename)
        elif file_id:
            file_obj = File(file_id= file_id, filename=filename)

        return MessageSegment("file", {"file": file_obj})
    
    def get_content_type(self) -> str:
        """获取消息段对应的内容类型"""
        mapping = {
            "text": ContentType.TEXT_PLAIN,
            "markdown": ContentType.TEXT_MARKDOWN,
            "file": ContentType.VOCECHAT_FILE,
        }
        return mapping.get(self.type, ContentType.TEXT_PLAIN).value
    
    def get_data(self) -> Union[str, Dict[str, Any]]:
        """获取消息段的数据表示"""
        if self.type == "file":
            return {"data": self.data.get("file", "")}
        return self.data.get("text", "")

class Message(BaseMessage[MessageSegment]):
    @classmethod
    @override
    def get_segment_class(cls) -> Type[MessageSegment]:
        return MessageSegment

    @staticmethod
    @override
    def _construct(msg: str) -> Iterable[MessageSegment]:
        # 将字符串构造为文本消息段
        yield MessageSegment.text(msg)
    
    def extract_mentions(self) -> List[int]:
        """从消息中提取提及的用户ID列表"""
        mentions = []
        for segment in self:
            if segment.type == "mention":
                user_id = segment.data.get("user_id")
                if user_id is not None:
                    mentions.append(user_id)
        return mentions
    
    def get_content_type(self) -> str:
        """获取消息的内容类型"""
        # 如果消息包含非文本类型，返回第一个非文本类型的content_type
        for segment in self:
            if segment.type != "text":
                return segment.get_content_type()
        return ContentType.TEXT_PLAIN.value
    
    def get_message_body(self) -> Union[str, Dict[str, Any]]:
        """获取消息的请求体"""
        # 如果消息是纯文本，直接返回字符串
        if all(seg.type == "text" for seg in self):
            return str(self)
        
        # 如果消息包含文件类型，返回文件路径
        for segment in self:
            if segment.type == "file":
                return segment.get_data()
        
        # 否则返回合并后的文本内容
        return str(self)
    
    def __str__(self) -> str:
        """将消息转换为纯文本表示"""
        return "".join(str(seg) for seg in self)