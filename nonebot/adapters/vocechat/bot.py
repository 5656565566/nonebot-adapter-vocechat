import json
import mimetypes
import re
from typing import TYPE_CHECKING, Any

from nonebot.adapters import Bot as BaseBot
from nonebot.drivers import Response, URL
from nonebot.message import handle_event
from typing_extensions import override

from .api import API, ContentType
from .config import BotConfig
from .event import Event, MessageEvent
from .message import File, Message, MessageSegment
from .utils import get_mime_type, log

if TYPE_CHECKING:
    from .adapter import Adapter

def _check_reply(bot: "Bot", event: MessageEvent) -> None:
    if event.reply is None:
        return

    # 需通过后续的回复缓存功能新增 才能完美实现


def _check_at_me(bot: "Bot", event: MessageEvent) -> None:
    """检查消息首尾是否 @ 机器人 并移除对应文本"""
    if not event.message:
        return

    user_id = str(getattr(bot, "user_id", ""))
    if not user_id:
        return

    first_msg_seg = event.message[0]
    if first_msg_seg.type == "text":
        first_text = first_msg_seg.data["text"].lstrip()
        if match := re.match(rf"^@{user_id}(?:\s+|$)", first_text):
            event.to_me = True
            first_msg_seg.data["text"] = first_text[match.end():]
            if not first_msg_seg.data["text"]:
                del event.message[0]

    if not event.message:
        return

    last_msg_seg = event.message[-1]
    if last_msg_seg.type != "text":
        return

    last_text = last_msg_seg.data["text"].rstrip()
    if re.search(rf"(?:\s+|^)@{user_id}$", last_text):
        event.to_me = True
        last_msg_seg.data["text"] = re.sub(rf"(?:\s+|^)@{user_id}$", "", last_text).rstrip()
        if not last_msg_seg.data["text"]:
            del event.message[-1]


def _check_nickname(bot: "Bot", event: MessageEvent) -> None:
    """检查消息开头是否存在昵称，去除并赋值 `event.to_me`

    Args:
        bot: Bot 对象
        event: MessageEvent 对象
    """
    if not event.message:
        return
    
    first_msg_seg = event.message[0]
    if first_msg_seg.type != "text":
        return

    nicknames = {re.escape(n) for n in bot.config.nickname}
    if not nicknames:
        return
    
    nickname_regex = "|".join(nicknames)
    first_text = first_msg_seg.data["text"]
    if m := re.search(rf"^({nickname_regex})([\s,，]*|$)", first_text, re.IGNORECASE):
        event.to_me = True
        first_msg_seg.data["text"] = first_text[m.end():]  # 移除昵称部分

class Bot(BaseBot):
    """
    VoceChat 协议 Bot 适配
    """
    adapter: "Adapter"

    @override
    def __init__(self, adapter: "Adapter", self_id: str, botConfig: BotConfig) -> None:
        super().__init__(adapter, self_id)
        self.self_id = self_id
        self.user_id = botConfig.user_id
        self.server_base = URL(botConfig.server)
        self.api_key = botConfig.api_key

    async def handle_event(self, event: Event) -> None:
        """处理事件"""
        if isinstance(event, MessageEvent):
            event.original_message = event.get_message()
            # _check_reply(self, event)
            _check_at_me(self, event)
            _check_nickname(self, event)

        await handle_event(self, event)

    async def send_message(
        self,
        message: Message,
        *,
        user_id: int | None = None,
        group_id: int | None = None,
        reply: int | None = None,
        **kwargs: Any,
    ) -> int | str | None:
        """发送消息到指定会话
        user_id group_id reply 三选一
        
        Args:
            message: 要发送的消息
            user_id: 私聊的用户id
            group_id: 群聊的群id
            reply: 回复的消息ID
            **kwargs: 其他参数
        """
        _ = kwargs
        message_id: int | str | None = None
        message.reduce()

        for message_segment in message:
            content_type: str = ContentType.TEXT_PLAIN.value
            content: str | dict[str, Any] | None = None
            properties: dict[str, Any] | None = None
            request = None

            if message_segment.type == "file":
                try:
                    file: File = message_segment.data["file"]
                    content_type = ContentType.VOCECHAT_FILE.value

                    if file.file_id:
                        content = file.file_id
                    else:
                        file_result = await self.upload_file(file)
                        content = file_result.get("path")
                        properties = file_result.get("image_properties")

                except Exception as e:
                    log("ERROR", f"File upload failed: {e}")
                    raise RuntimeError(f"Failed to upload file: {e}") from e
                    
            elif message_segment.type == "markdown":
                content_type = ContentType.TEXT_MARKDOWN.value
                content = message_segment.data.get("text")

            else:
                content = message_segment.data.get("text")
        
            try:
                if reply:
                    request = API.reply(
                        mid=reply,
                        content_type=content_type,
                        content=content,
                        properties=properties
                    )
                elif group_id:
                    request = API.send_to_group(
                        gid=group_id,
                        content_type=content_type,
                        content=content,
                        properties=properties
                    )
                elif user_id:
                    request = API.send_to_user(
                        uid=user_id,
                        content_type=content_type,
                        content=content,
                        properties=properties
                    )
                
                if request:
                    message_id = await self.call_api("send_message", request=request)
            except Exception as e:
                log("ERROR", f"Failed to send message: {e}")
                raise

        return message_id

    @override
    async def send(
        self,
        event: Event,
        message: str | Message | MessageSegment,
        **kwargs: Any,
    ) -> int | str | None:
        """发送消息
        
        Args:
            event: 事件对象
            message: 要发送的消息 可以是字符串、Message或MessageSegment
            **kwargs: 其他参数
        """
        from_uid = getattr(event, "from_uid", None)
        if not from_uid:
            raise ValueError("Event has no from_uid")

        target = getattr(event, "target", None)
        if not target:
            raise ValueError("Event has no target")

        if isinstance(message, str):
            msg = Message(MessageSegment.text(message))
        elif isinstance(message, MessageSegment):
            msg = Message(message)
        else:
            msg = message

        group_id = getattr(target, "gid", None)
        user_id = None if group_id else from_uid

        return await self.send_message(
            message=msg,
            user_id=user_id,
            group_id=group_id,
            **kwargs
        )

    async def download_file(
        self,
        file_id: str | None = None,
        message: Message | MessageSegment | None = None,
    ) -> bytes:
        """
        下载文件

        Args:
            file_id: 文件ID
            message: 文件信息

        Returns:
            文件数据
        """

        if isinstance(message, Message):
            for message_segment in message:
                if message_segment.type == "file":
                    file_obj = message_segment.data.get("file")
                    if file_obj:
                        file_id = getattr(file_obj, "file_id", None)
                    if file_id:
                        break

        if isinstance(message, MessageSegment):
            if message.type == "file":
                file_obj = message.data.get("file")
                if file_obj:
                    file_id = getattr(file_obj, "file_id", None)

        if not file_id:
            return b""

        response = await self.call_api("download_file", file_id=file_id)
        return response.content

    async def upload_file(self, file: File) -> dict[str, Any]:
        """
        上传文件
        
        Args:
            file: File对象
        
        Returns:
            包含文件信息的字典，如
            {
                "path": "string",
                "size": 0,
                "hash": "string",
                "image_properties": {
                    "width": 0,
                    "height": 0
                }
            }
            其中 path 为消息发送所需要的字段
        """
        file_data = await file.get_data()
        mime_type = get_mime_type(file_data)
        extension = mimetypes.guess_extension(mime_type)
        file_name = file.filename

        content_type = ContentType.VOCECHAT_FILE.value
    
        # 根据MIME类型确定内容类型
        if mime_type:
            if mime_type.startswith("audio/"):
                content_type = mime_type
            if mime_type.startswith("image/"):
                content_type = mime_type
            if mime_type.startswith("video/"):
                content_type = mime_type

        if not file_name:
            file_name = mime_type.split("/")[0] if mime_type else "unknown"

        if extension and not file_name.lower().endswith(extension.lower()):
            file_name += extension

        # 验证文件数据
        if not file_data:
            raise ValueError("File data cannot be empty")
    
        # 验证文件大小
        max_size = 50 * 1024 * 1024  # 50MB
        if len(file_data) > max_size:
            raise ValueError(f"File too large: {len(file_data)} bytes (max: {max_size} bytes)")
    
        try:
            # 准备文件上传
            log("DEBUG", f"Preparing file upload: {file_name} ({len(file_data)} bytes)")
            
            prepare_result: Response = await self.call_api(
                api="file_prepare",
                content_type=content_type,
                filename=file_name,
                raw=True,
            )
            
            # 解析准备结果
            if prepare_result.status_code != 200:
                raise RuntimeError(f"File prepare failed with status {prepare_result.status_code}")
            
            try:
                # 尝试解析 JSON 响应
                prepare_content = prepare_result.content
                file_id = None

                if isinstance(prepare_content, bytes):
                    prepare_content = prepare_content.decode("utf-8")
                elif prepare_content is None:
                    prepare_content = ""
                else:
                    prepare_content = str(prepare_content)

                # 如果是纯字符串 file_id
                if prepare_content.startswith('"') and prepare_content.endswith('"'):
                    file_id = prepare_content.strip('"')
            
            except Exception as e:
                log("ERROR", f"Failed to parse prepare result: {e}")
                raise RuntimeError(f"Invalid prepare response format: {e}")
            
            if not file_id:
                raise RuntimeError("No file_id returned from prepare request")
            
            log("DEBUG", f"File prepared with ID: {file_id}")
            
            # 上传文件数据
            upload_result: Response = await self.call_api(
                api="file_upload",
                file_id=file_id,
                chunk_data=file_data,
                chunk_is_last=True,
                raw=True,
            )

            if upload_result.status_code != 200:
                raise RuntimeError(f"File upload failed with status {upload_result.status_code}")
            
            # 解析上传结果
            try:
                upload_content = upload_result.content
                if isinstance(upload_content, bytes):
                    upload_content = upload_content.decode("utf-8")
                elif upload_content is None:
                    upload_content = ""
                else:
                    upload_content = str(upload_content)
            
                # 返回的是 JSON 格式
                result_data = json.loads(upload_content)
            
                # 确保有 path 字段
                if "path" not in result_data:
                    raise RuntimeError("No file path returned from upload")
            
            except json.JSONDecodeError as e:
                log("ERROR", f"Failed to parse upload result as JSON: {e}")
                result_data = {}
            except Exception as e:
                log("ERROR", f"Failed to parse upload result: {e}")
                raise RuntimeError(f"Invalid upload response format: {e}")
            
            log("DEBUG", f"File uploaded successfully: {file_name} -> {result_data.get('path')}")
            
            return result_data
            
        except Exception as e:
            log("ERROR", f"File upload failed for {file_name}: {e}")
            raise RuntimeError(f"File upload failed: {e}") from e

    async def command_add(self, command: str, description: str) -> Any:
        request = API.command_add(command, description)
        return await self.call_api("command_add", request=request)

    async def command_get(self) -> Any:
        request = API.command_get()
        return await self.call_api("command_get", request=request)

    async def command_delete(self, id: int) -> Any:
        request = API.command_delete(id)
        return await self.call_api("command_delete", request=request)

    async def command_update(self, id: int, command: str, description: str) -> Any:
        request = API.command_update(id, command, description)
        return await self.call_api("command_update", request=request)

    async def edit(self, mid: int, message: str | Message | MessageSegment, properties: dict[str, Any] | None = None) -> Any:
        if isinstance(message, str):
            msg = Message(MessageSegment.text(message))
        elif isinstance(message, MessageSegment):
            msg = Message(message)
        else:
            msg = message

        msg.reduce()
        content_type: str = ContentType.TEXT_PLAIN.value
        content: str | dict[str, Any] | None = None

        for message_segment in msg:
            if message_segment.type == "file":
                try:
                    file: File = message_segment.data["file"]
                    content_type = ContentType.VOCECHAT_FILE.value
                    if file.file_id:
                        content = file.file_id
                    else:
                        file_result = await self.upload_file(file)
                        content = {"path": file_result.get("path")}
                        properties = properties or {}
                        properties.update(file_result.get("image_properties", {}))
                except Exception as e:
                    log("ERROR", f"File upload failed: {e}")
                    raise RuntimeError(f"Failed to upload file: {e}") from e
            elif message_segment.type == "markdown":
                content_type = ContentType.TEXT_MARKDOWN.value
                content = message_segment.data.get("text")
            else:
                content = message_segment.data.get("text")

        request = API.edit(mid, content_type, content, properties)
        return await self.call_api("edit", request=request)

    async def delete(self, mid: int) -> Any:
        request = API.delete(mid)
        return await self.call_api("delete", request=request)

    async def secret_get(self) -> Any:
        request = API.secret_get()
        return await self.call_api("secret_get", request=request)

    async def secret_set(self, secret: str) -> Any:
        request = API.secret_set(secret)
        return await self.call_api("secret_set", request=request)

    async def user_messages(self, uid: int) -> Any:
        request = API.user_messages(uid)
        return await self.call_api("user_messages", request=request)

    async def group_messages(self, gid: int) -> Any:
        request = API.group_messages(gid)
        return await self.call_api("group_messages", request=request)