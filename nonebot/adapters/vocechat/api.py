from nonebot.internal.driver import Request

from typing import Optional, Any, Dict, Union
from enum import Enum

import json

class ContentType(Enum):
    """在 VoceChat 文档中的 ContentType"""

    TEXT_PLAIN = "text/plain"
    TEXT_MARKDOWN = "text/markdown"
    VOCECHAT_FILE = "vocechat/file"
    VOCECHAT_AUDIO = "vocechat/audio"
    VOCECHAT_ARCHIVE = "vocechat/archive"

    def __str__(self):
        return self.value

class API:

    @staticmethod
    def bot(public_only: bool):
        request = Request(
            "GET",
            "/api/bot",
            headers = {
                "Accept": "application/json; charset=utf-8"
            },
            params= {"public_only": public_only}
        )

        return request
    
    @staticmethod
    def send_to_user(uid: int, content_type: Union[ContentType, str], content: Any, properties: Optional[Dict[str, Any]] = None):

        if isinstance(content_type, ContentType):
            content_type = content_type.value

        headers = {
            "Accept": "application/json; charset=utf-8",
            "Content-Type" : content_type
        }

        if properties:
            headers["X-Properties"] = json.dumps(properties)

        if isinstance(content, Dict):
            content = json.dumps(content)

        request = Request(
            "POST",
            f"/api/bot/send_to_user/{uid}",
            headers = headers,
            data= content
        )

        return request
    

    @staticmethod
    def send_to_group(gid: int, content_type: Union[ContentType, str], content: Any, properties: Optional[Dict[str, Any]] = None):

        if isinstance(content_type, ContentType):
            content_type = content_type.value

        headers = {
            "Accept": "application/json; charset=utf-8",
            "Content-Type" : content_type
        }

        if properties:
            headers["X-Properties"] = json.dumps(properties)

        if isinstance(content, Dict):
            content = json.dumps(content)

        request = Request(
            "POST",
            f"/api/bot/send_to_group/{gid}",
            headers = headers,
            data= content
        )

        return request
    

    @staticmethod
    def reply(mid: int, content_type: Union[ContentType, str], content: Any, properties: Optional[Dict[str, Any]] = None):

        if isinstance(content_type, ContentType):
            content_type = content_type.value

        headers = {
            "Accept": "application/json; charset=utf-8",
            "Content-Type" : content_type
        }

        if properties:
            headers["X-Properties"] = json.dumps(properties)

        if isinstance(content, Dict):
            content = json.dumps(content)

        request = Request(
            "POST",
            f"/api/bot/reply/{mid}",
            headers = headers,
            data= content
        )

        return request
    
    @staticmethod
    def send_mail(data: Any, content: Any):

        if isinstance(content, Dict):
            content = json.dumps(content)

        request = Request(
            "POST",
            "/api/bot/send_mail",
            headers = {
                "Accept": "*/*",
                "Content-Type": "application/json; charset=utf-8"
            },
            data= data
        )

        return request
    
    @staticmethod
    def user(uid: int):
        request = Request(
            "GET",
            f"/api/bot/user/uid?uid={uid}",
            headers = {
                "Accept": "application/json; charset=utf-8",
            },
        )

        return request
    
    @staticmethod
    def group(gid: int):
        request = Request(
            "GET",
            f"/api/bot/group/gid?gid={gid}",
            headers = {
                "Accept": "application/json; charset=utf-8",
            },
        )

        return request
    
    @staticmethod
    def file_prepare(content_type: Union[str, ContentType], filename: str):

        if isinstance(content_type, ContentType):
            content_type = content_type.value

        request = Request(
            "POST",
            "/api/bot/file/prepare",
            headers = {
                "Accept": "application/json; charset=utf-8",
                "Content-Type": "application/json; charset=utf-8"
            },
            json= {"content_type": content_type, "filename": filename}
        )

        return request
    

    @staticmethod
    def file_upload(file_id: str, chunk_data: bytes, chunk_is_last: bool):
        files = {
            "file_id": (None, file_id),
            "chunk_is_last": (None, str(chunk_is_last).lower()),
            "chunk_data": ("chunk", chunk_data, "application/octet-stream")
        }
        
        request = Request(
            "POST",
            "/api/bot/file/upload",
            headers={
                "Accept": "application/json; charset=utf-8",
            },
            files=files
        )
        
        return request

    @staticmethod
    def command_add(command: str, description: str):
        request = Request(
            "POST",
            "/api/bot/command",
            headers = {
                "Accept": "application/json; charset=utf-8",
            },
            json= {"command": command, "description": description}
        )

        return request

    @staticmethod
    def command_get():
        request = Request(
            "GET",
            "/api/bot/command",
            headers = {
                "Accept": "application/json; charset=utf-8",
            },
        )

        return request

    @staticmethod
    def command_delete(id: int):
        request = Request(
            "DELETE",
            f"/api/bot/command/{id}",
            headers = {
                "Accept": "application/json; charset=utf-8",
            }
        )

        return request

    @staticmethod
    def command_update(id: int, command: str, description: str):
        request = Request(
            "PUT",
            f"/api/bot/command/{id}",
            headers = {
                "Accept": "application/json; charset=utf-8",
            },
            json= {"command": command, "description": description}
        )

        return request
    
    @staticmethod
    def download_file(file_id: str):
        request = Request(
            "GET",
            f"/api/resource/file?file_path={file_id}&download=true",
            headers = {
                "Accept": "application/octet-stream",
            },
        )

        return request