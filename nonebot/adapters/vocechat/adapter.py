import inspect
import json
from datetime import datetime
from typing import Any, cast

from nonebot import get_plugin_config
from nonebot.drivers import (
    ASGIMixin,
    Driver,
    HTTPClientMixin,
    HTTPServerSetup,
    Request,
    Response,
    URL,
)
from nonebot.internal.adapter import Adapter as BaseAdapter
from typing_extensions import override

from .api import API
from .bot import Bot
from .config import Config
from .event import Event, GroupMessageEvent, PrivateMessageEvent, Reply
from .exception import (
    ActionFailed,
    ApiNotAvailable,
    ForbiddenException,
    NetworkError,
    NotFoundException,
    RateLimitException,
    ServerError,
    UnauthorizedException,
)
from .utils import MessageCache, log

class Adapter(BaseAdapter):
    @override
    def __init__(self, driver: Driver, **kwargs: Any) -> None:
        super().__init__(driver, **kwargs)
        self.adapter_config: Config = get_plugin_config(Config)
        self.message_cache: dict[str, MessageCache] = {}
        self.setup()

    @classmethod
    @override
    def get_name(cls) -> str:
        """适配器名称"""
        return "VoceChat"

    def setup(self) -> None:
        if not isinstance(self.driver, ASGIMixin):
            raise RuntimeError(
                f"Current driver {self.config.driver} doesn't support asgi server!"
                f"{self.get_name()} Adapter need a asgi server driver to work."
            )
        if not isinstance(self.driver, HTTPClientMixin):
            raise RuntimeError(
                f"Current driver {self.config.driver} does not support http client requests! "
                f"{self.get_name()} Adapter need a HTTPClient Driver to work."
            )
        

        @self.on_ready
        async def _() -> None:
            for vocechat_bot in self.adapter_config.vocechat_bots:
                self.bot_connect(
                    Bot(
                        adapter=self,
                        self_id=vocechat_bot.name or vocechat_bot.user_id,
                        botConfig=vocechat_bot,
                    )
                )

        for path in (
            "/vocechat/webhook/{name}",
            "/vocechat/webhook/{name}/",
            "/vocechat/{name}",
            "/vocechat/{name}/",
        ):
            for method in ("GET", "POST"):
                self.setup_http_server(
                    HTTPServerSetup(
                        URL(path),
                        method,
                        f"{self.get_name()} Webhook",
                        self._handle_http,
                    )
                )

    @staticmethod
    def _raise_api_exception(response: Response) -> None:
        status_code = response.status_code

        if status_code == 401:
            raise UnauthorizedException(response)
        if status_code == 403:
            raise ForbiddenException(response)
        if status_code == 404:
            raise NotFoundException(response)
        if status_code == 429:
            raise RateLimitException(response)
        if status_code >= 500:
            raise ServerError(response)
        raise ActionFailed(response)

    @staticmethod
    def _normalize_response_content(response: Response) -> bytes:
        response_content = response.content

        if isinstance(response_content, bytes):
            return response_content
        if response_content is None:
            return b""
        return str(response_content).encode("utf-8")

    @override
    async def _call_api(self, bot: Bot, api: str, **data: Any) -> Any:
        """`Adapter` 实际调用 api 的逻辑实现函数 实现该方法以调用 api

        参数:
            api: API 名称
            data: API 数据
        """
        log("DEBUG", f"call api {api}")

        request: Request | None = None
        raw = bool(data.pop("raw", False))

        if hasattr(API, api):
            api_method = getattr(API, api)
            sign = inspect.signature(api_method)

            for param in sign.parameters.values():
                if param.name == "self":
                    continue

                if param.name not in data:
                    if param.default == inspect.Parameter.empty:
                        log("ERROR", f"Missing required parameter: {param.name} for API {api}")
                        raise TypeError(f"Missing required parameter: {param.name} for API {api}")
                    else:
                        data[param.name] = param.default

            request = api_method(**data)
        else:
            request = cast(Request | None, data.get("request"))

        if request is None:
            raise ApiNotAvailable()

        request.headers["x-api-key"] = str(bot.api_key)
        server_base = str(bot.server_base).rstrip("/")
        request_path = str(request.url)
        request.url = URL(f"{server_base}{request_path}")

        try:
            response = await self.request(request)
        except ApiNotAvailable:
            raise
        except Exception as e:
            log("ERROR", f"Network error when calling API {api}: {e}")
            raise NetworkError(str(e)) from e

        if response.status_code >= 400:
            log(
                "DEBUG",
                "VoceChat request failed: "
                f"api={api}, method={request.method}, url={request.url}, "
                f"status={response.status_code}, "
                f"response={self._normalize_response_content(response)!r}",
            )
            log("ERROR", f"API {api} failed with status code {response.status_code}")
            self._raise_api_exception(response)

        if raw:
            return response

        content_type = response.headers.get("content-type", "").lower()
        normalized_content = self._normalize_response_content(response)

        if "application/json" in content_type:
            try:
                return json.loads(normalized_content) if normalized_content else {}
            except json.JSONDecodeError as e:
                log("ERROR", f"Failed to decode JSON response from API {api}: {e}")
                raise ActionFailed(response) from e

        if api == "download_file" or "octet-stream" in content_type:
            return response

        try:
            return normalized_content.decode("utf-8")
        except UnicodeDecodeError:
            return normalized_content


    async def _handle_http(self, request: Request) -> Response:
        """处理 VoceChat webhook 请求"""
        if request.method == "GET":
            return Response(status_code=200)

        try:
            path_parts = request.url.path.strip("/").split("/")
            name = path_parts[-1]
            bot = self.bots.get(name)

            if not bot:
                return Response(status_code=404, content="Not Found Bot")

            vocechat_bot = cast(Bot, bot)

            try:
                raw_content = request.content
                if isinstance(raw_content, bytes):
                    payload = json.loads(raw_content.decode("utf-8")) if raw_content else {}
                elif isinstance(raw_content, str):
                    payload = json.loads(raw_content) if raw_content else {}
                else:
                    payload = {}
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
                return Response(status_code=400, content="Invalid JSON")

            event = self._parse_event(payload, vocechat_bot)

            if event:
                await vocechat_bot.handle_event(event)

            return Response(status_code=200)

        except Exception as e:
            log("ERROR", "Error handling VoceChat webhook", e)
            return Response(status_code=500, content=str(e))

    def _parse_event(self, payload: dict[str, Any], bot: Bot) -> Event | None:
        """解析 VoceChat 事件"""
        try:
            timestamp = payload.get("created_at", 0)

            event_data = {
                "created_at": timestamp,
                "from_uid": payload.get("from_uid", 0),
                "mid": payload.get("mid", 0),
                "target": payload.get("target", {}),
                "self_uid": bot.user_id,
                "time": datetime.fromtimestamp(timestamp / 1000) if timestamp is not None else datetime.now(),
                "message_id": payload.get("mid"),
            }

            detail = payload.get("detail", {})

            if isinstance(detail, dict):
                event = None
                bot_self_id = bot.self_id
                if self.message_cache.get(bot_self_id) is None:
                    self.message_cache[bot_self_id] = MessageCache(self.adapter_config.vocechat_history_length)

                detail_type = detail.get("type")

                is_group = payload.get("target", {}).get("gid") is not None

                if detail_type in ("normal", "reply"):
                    event_data["detail"] = detail

                    if is_group:
                        event = GroupMessageEvent.model_validate(event_data)
                    else:
                        event = PrivateMessageEvent.model_validate(event_data)

                    if detail_type == "reply":
                        reply_id = detail.get("mid", 0)
                        cached_event = self.message_cache[bot_self_id].get(reply_id)
                        event.reply = Reply(
                            mid=reply_id,
                            message=cached_event.message if cached_event else None
                        )

                    self.message_cache[bot_self_id].add(event.mid, event)

                    return event

            log("WARNING", f"Unknown event type: {payload}")
            return None

        except Exception as e:
            log("ERROR", "Error parsing VoceChat event", e)
            return None