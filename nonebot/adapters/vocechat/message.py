import io
import re
from pathlib import Path
from typing import Any, Iterable, Literal

from nonebot.adapters import Message as BaseMessage
from nonebot.adapters import MessageSegment as BaseMessageSegment
from typing_extensions import override

from .api import ContentType


class File:
    """文件类 方便处理文件"""

    def __init__(
        self,
        file: str | bytes | io.BytesIO | Path | None = None,
        file_id: str | None = None,
        filename: str | None = None,
    ) -> None:
        if file is None and file_id is None:
            raise ValueError("Either 'file' or 'file_id' must be provided")

        self._path: Path | None = None
        self._data: bytes | None = None

        if isinstance(file, (str, Path)):
            self._path = Path(file)
            if not filename:
                filename = self._path.name
        elif isinstance(file, bytes):
            self._data = file
        elif isinstance(file, io.BytesIO):
            self._data = file.getvalue()

        self.file_id = file_id
        self.filename = filename

    async def get_data(self) -> bytes:
        if self._data is not None:
            return self._data
        if self._path is not None:
            with open(self._path, "rb") as f:
                return f.read()

        raise ValueError("No valid data source provided")

    def __str__(self) -> str:
        return self.filename or self.file_id or "Unknown"


class MessageSegment(BaseMessageSegment["Message"]):
    @staticmethod
    def _media(
        segment_type: Literal["file", "image", "audio", "video"],
        file: str | bytes | io.BytesIO | Path | None = None,
        file_id: str | None = None,
        filename: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> "MessageSegment":
        file_obj = File(file=file, file_id=file_id, filename=filename)
        data: dict[str, Any] = {"file": file_obj}
        if properties:
            data["properties"] = properties
        return MessageSegment(segment_type, data)

    @classmethod
    @override
    def get_message_class(cls) -> type["Message"]:
        return Message

    @override
    def __str__(self) -> str:
        if self.is_text():
            return self.data.get("text", "")
        elif self.type == "mention":
            return f"@{self.data.get('user_id', '')} "
        elif self.type == "markdown":
            return "[Markdown]"
        elif self.type in {"file", "image", "audio", "video"}:
            labels = {
                "file": "File",
                "image": "Image",
                "audio": "Audio",
                "video": "Video",
            }
            return f"[{labels.get(self.type, 'File')}: {self.data.get('file', '')}]"
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
    def file(
        file: str | bytes | io.BytesIO | Path | None = None,
        file_id: str | None = None,
        filename: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> "MessageSegment":
        """创建文件消息段"""
        return MessageSegment._media(
            "file", file=file, file_id=file_id, filename=filename, properties=properties
        )
    
    @staticmethod
    def archive(archive_id: str) -> "MessageSegment":
        """创建合并转发消息段"""
        return MessageSegment("archive", {"archive_id": archive_id})

    @staticmethod
    def image(
        file: str | bytes | io.BytesIO | Path | None = None,
        file_id: str | None = None,
        filename: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> "MessageSegment":
        """创建图片消息段"""
        return MessageSegment._media(
            "image", file=file, file_id=file_id, filename=filename, properties=properties
        )

    @staticmethod
    def audio(
        file: str | bytes | io.BytesIO | Path | None = None,
        file_id: str | None = None,
        filename: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> "MessageSegment":
        """创建音频消息段"""
        return MessageSegment._media(
            "audio", file=file, file_id=file_id, filename=filename, properties=properties
        )

    @staticmethod
    def video(
        file: str | bytes | io.BytesIO | Path | None = None,
        file_id: str | None = None,
        filename: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> "MessageSegment":
        """创建视频消息段"""
        return MessageSegment._media(
            "video", file=file, file_id=file_id, filename=filename, properties=properties
        )

    @staticmethod
    def mention(user_id: int) -> "MessageSegment":
        """提及消息段"""
        return MessageSegment("mention", {"user_id": user_id})

    def get_content_type(self) -> str:
        """获取消息段对应的内容类型"""
        mapping = {
            "text": ContentType.TEXT_PLAIN,
            "mention": ContentType.TEXT_PLAIN,
            "markdown": ContentType.TEXT_MARKDOWN,
            "file": ContentType.VOCECHAT_FILE,
            "image": ContentType.VOCECHAT_FILE,
            "audio": ContentType.VOCECHAT_AUDIO,
            "video": ContentType.VOCECHAT_FILE,
            "archive": ContentType.VOCECHAT_ARCHIVE,
        }
        return mapping.get(self.type, ContentType.TEXT_PLAIN).value
    
    def get_data(self) -> str | dict[str, Any]:
        """获取消息段的数据表示"""
        if self.type in {"file", "image", "audio", "video"}:
            return {"data": self.data.get("file", "")}
        if self.type == "mention":
            return f"@{self.data.get('user_id', '')} "
        return self.data.get("text", "")

class Message(BaseMessage[MessageSegment]):
    @classmethod
    @override
    def get_segment_class(cls) -> type[MessageSegment]:
        return MessageSegment

    @staticmethod
    @override
    def _construct(msg: str) -> Iterable[MessageSegment]:
        # 将字符串构造为文本和提及消息段
        pattern = re.compile(r"@(\d+)\s")
        last_end = 0

        for match in pattern.finditer(msg):
            start, end = match.span()
            if start > last_end:
                yield MessageSegment.text(msg[last_end:start])
            yield MessageSegment.mention(int(match.group(1)))
            last_end = end

        if last_end < len(msg):
            yield MessageSegment.text(msg[last_end:])
    
    def extract_mentions(self) -> list[int]:
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
    
    def get_message_body(self) -> str | dict[str, Any]:
        """获取消息的请求体"""
        # 如果消息是纯文本，直接返回字符串
        if all(seg.type == "text" for seg in self):
            return str(self)
        
        # 如果消息包含文件类型，返回文件路径
        for segment in self:
            if segment.type in {"file", "image", "audio", "video"}:
                return segment.get_data()
        
        # 否则返回合并后的文本内容
        return str(self)
    
    def __str__(self) -> str:
        """将消息转换为纯文本表示"""
        return "".join(str(seg) for seg in self)
    
    def reduce(self) -> None:
        """合并消息内连续的纯文本段"""
        index = 1
        while index < len(self):
            if self[index - 1].type == "text" and self[index].type == "text":
                self[index - 1].data["text"] += self[index].data["text"]
                del self[index]
            elif self[index - 1].type == "mention" and self[index].type == "mention":
                index += 1
            else:
                index += 1