import json
from enum import Enum
from typing import Any

from nonebot.internal.driver import Request


class ContentType(Enum):
    """VoceChat 文档中的 ContentType"""

    TEXT_PLAIN = "text/plain"
    TEXT_MARKDOWN = "text/markdown"
    VOCECHAT_FILE = "vocechat/file"
    VOCECHAT_AUDIO = "vocechat/audio"
    VOCECHAT_ARCHIVE = "vocechat/archive"

    def __str__(self) -> str:
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
    def send_to_user(
        uid: int,
        content_type: ContentType | str,
        content: Any,
        properties: dict[str, Any] | None = None,
    ) -> Request:

        if isinstance(content_type, ContentType):
            content_type = content_type.value

        headers = {
            "Accept": "application/json; charset=utf-8",
            "Content-Type" : content_type
        }

        if properties:
            headers["X-Properties"] = json.dumps(properties)

        if isinstance(content, dict):
            content = json.dumps(content)

        request = Request(
            "POST",
            f"/api/bot/send_to_user/{uid}",
            headers = headers,
            data= content
        )

        return request
    

    @staticmethod
    def send_to_group(
        gid: int,
        content_type: ContentType | str,
        content: Any,
        properties: dict[str, Any] | None = None,
    ) -> Request:

        if isinstance(content_type, ContentType):
            content_type = content_type.value

        headers = {
            "Accept": "application/json; charset=utf-8",
            "Content-Type" : content_type
        }

        if properties:
            headers["X-Properties"] = json.dumps(properties)

        if isinstance(content, dict):
            content = json.dumps(content)

        request = Request(
            "POST",
            f"/api/bot/send_to_group/{gid}",
            headers = headers,
            data= content
        )

        return request
    

    @staticmethod
    def reply(
        mid: int,
        content_type: ContentType | str,
        content: Any,
        properties: dict[str, Any] | None = None,
    ) -> Request:

        if isinstance(content_type, ContentType):
            content_type = content_type.value

        headers = {
            "Accept": "application/json; charset=utf-8",
            "Content-Type" : content_type
        }

        if properties:
            headers["X-Properties"] = json.dumps(properties)

        if isinstance(content, dict):
            content = json.dumps(content)

        request = Request(
            "POST",
            f"/api/bot/reply/{mid}",
            headers = headers,
            data= content
        )

        return request
    
    @staticmethod
    def send_mail(data: dict[str, Any], content: Any) -> Request:
        payload = data.copy()
        
        if isinstance(content, dict):
            payload["content"] = json.dumps(content)
        else:
            payload["content"] = str(content)

        request = Request(
            "POST",
            "/api/bot/send_mail",
            headers={
                "Content-Type": "application/json"
            },
            content=json.dumps(payload)
        )
        return request
    
    @staticmethod
    def user(uid: int) -> Request:
        request = Request(
            "GET",
            f"/api/bot/user/{uid}",
            headers = {
                "Accept": "application/json; charset=utf-8",
            },
        )

        return request
    
    @staticmethod
    def group(gid: int) -> Request:
        request = Request(
            "GET",
            f"/api/bot/group/{gid}",
            headers = {
                "Accept": "application/json; charset=utf-8",
            },
        )

        return request
    
    @staticmethod
    def file_prepare(content_type: str | ContentType, filename: str) -> Request:

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
    def file_upload(file_id: str, chunk_data: bytes, chunk_is_last: bool) -> Request:
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
    def command_add(command: str, description: str) -> Request:
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
    def command_get() -> Request:
        request = Request(
            "GET",
            "/api/bot/command",
            headers = {
                "Accept": "application/json; charset=utf-8",
            },
        )

        return request

    @staticmethod
    def command_delete(id: int) -> Request:
        request = Request(
            "DELETE",
            f"/api/bot/command/{id}",
            headers = {
                "Accept": "application/json; charset=utf-8",
            }
        )

        return request

    @staticmethod
    def command_update(id: int, command: str, description: str) -> Request:
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
    def download_file(file_id: str) -> Request:
        request = Request(
            "GET",
            f"/api/resource/file?file_path={file_id}&download=true",
            headers = {
                "Accept": "application/octet-stream",
            },
        )

        return request

    @staticmethod
    def edit(
        mid: int,
        content_type: ContentType | str,
        content: Any,
        properties: dict[str, Any] | None = None,
    ) -> Request:
        if isinstance(content_type, ContentType):
            content_type = content_type.value

        headers = {
            "Accept": "application/json; charset=utf-8",
            "Content-Type": content_type,
        }

        if properties:
            headers["X-Properties"] = json.dumps(properties)

        if isinstance(content, dict):
            content = json.dumps(content)

        return Request(
            "PUT",
            f"/api/bot/edit/{mid}",
            headers=headers,
            data=content,
        )

    @staticmethod
    def delete(mid: int) -> Request:
        return Request(
            "DELETE",
            f"/api/bot/delete/{mid}",
            headers={
                "Accept": "application/json; charset=utf-8",
            },
        )

    @staticmethod
    def secret_get() -> Request:
        return Request(
            "GET",
            "/api/bot/secret",
            headers={
                "Accept": "application/json; charset=utf-8",
            },
        )

    @staticmethod
    def secret_set(secret: str) -> Request:
        return Request(
            "PUT",
            "/api/bot/secret",
            headers={
                "Accept": "application/json; charset=utf-8",
                "Content-Type": "application/json; charset=utf-8",
            },
            json={"secret": secret},
        )

    @staticmethod
    def user_messages(uid: int) -> Request:
        return Request(
            "GET",
            f"/api/bot/user/{uid}/messages",
            headers={
                "Accept": "application/json; charset=utf-8",
            },
        )

    @staticmethod
    def group_messages(gid: int) -> Request:
        return Request(
            "GET",
            f"/api/bot/group/{gid}/messages",
            headers={
                "Accept": "application/json; charset=utf-8",
            },
        )