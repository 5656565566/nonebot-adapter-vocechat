from nonebot import get_plugin_config
from nonebot.drivers import (
    Request,
    ASGIMixin,
    HTTPClientMixin,
    HTTPServerSetup,
    URL
)
from nonebot.drivers import Response, Driver
from nonebot.internal.adapter import Adapter as BaseAdapter

from typing_extensions import override
from typing import Any, Dict, Optional
from datetime import datetime

import inspect
import json

from .bot import Bot
from .config import Config
from .event import *
from .utils import log, MessageCache
from .api import API

class Adapter(BaseAdapter):
    @override
    def __init__(self, driver: Driver, **kwargs: Any):
        super().__init__(driver, **kwargs)
        self.adapter_config: Config = get_plugin_config(Config)
        self.message_cache = MessageCache(self.adapter_config.message_cache_length)
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
        def _():
            for vocechat_bot in self.adapter_config.vocechat_bots:
                self.bot_connect(
                    Bot(
                        adapter= self,
                        self_id= vocechat_bot.name,
                        user_id = vocechat_bot.user_id,
                        api_key= vocechat_bot.api_key,
                        server_base= vocechat_bot.server
                        )
                    )

        self.setup_http_server(
            HTTPServerSetup(
                URL("/vocechat/webhook"),
                "POST",
                f"{self.get_name()} Webhook",
                self._handle_http,
            ),
        )
        self.setup_http_server(
            HTTPServerSetup(
                URL("/vocechat/webhook/"),
                "POST",
                f"{self.get_name()} Webhook Slash",
                self._handle_http,
            ),
        )

        self.setup_http_server(
            HTTPServerSetup(
                URL("/vocechat/webhook"),
                "GET",
                f"{self.get_name()} Webhook",
                self._handle_http,
            ),
        )
        self.setup_http_server(
            HTTPServerSetup(
                URL("/vocechat/webhook/"),
                "GET",
                f"{self.get_name()} Webhook Slash",
                self._handle_http,
            ),
        )

    @override
    async def _call_api(self, bot: Bot, api: str, **data: Any) -> Any:
        """`Adapter` 实际调用 api 的逻辑实现函数，实现该方法以调用 api。

        参数:
            api: API 名称
            data: API 数据
        """
        log("DEBUG", f"call api {api}")
        
        request = None
        raw = data.pop("raw", False)

        if hasattr(API, api):
            api_method = getattr(API, api)
            sign = inspect.signature(api_method)

            for param in sign.parameters.values():
                if param.name == "self":
                    continue

                if param.name not in data:
                    if param.default == inspect.Parameter.empty:
                        log("ERROR", f"Missing required parameter: {param.name} for API {api}")
                        data[param.name] = None
                    else:
                        data[param.name] = param.default
            
            request = api_method(**data)
        else:
            request = data.get("request", None)

        if request:
            request.headers["x-api-key"] = bot.api_key
            request.url = URL(f"{bot.server_base}{request.url}")

            try:
                response = await self.request(request)
                
                if raw:
                    return response
                    
                # 根据 Content-Type 决定如何处理响应
                content_type = response.headers.get("content-type", "").lower()
                
                if "application/json" in content_type:
                    return json.loads(response.content)
                elif api == "download_file" or "octet-stream" in content_type:
                    return response  # 返回二进制内容 修复下载文件也转换成 json 导致的问题
                else:
                    # 其他情况尝试解码为文本
                    try:
                        return response.content.decode("utf-8")
                    except UnicodeDecodeError:
                        return response.content
                
            except Exception as e:
                log("ERROR", f"Error calling API {api}: {e}")
                raise e


    async def _handle_http(self, request: Request) -> Response:
        """处理VoceChat Webhook请求"""
        try:
            bot_name = request.url.query.get("bot")
            
            if not bot_name:
                return Response(status_code=404, content="Not Found")

            if request.method == "GET": # 添加机器人需要验证
                return Response(status_code=200)
            
            bot = self.bots.get(bot_name)

            if not bot:
                return Response(status_code=404, content="Not Found Bot")

            try:
                payload = request.json
            except ValueError:
                return Response(status_code=400, content="Invalid JSON")
            
            event = self._parse_event(payload, bot)

            if event:
                await bot.handle_event(event)

            return Response(status_code=200)
        
        except Exception as e:
            log("ERROR", "Error handling VoceChat webhook", e)
            return Response(status_code=500, content=str(e))

    def _parse_event(self, payload: Dict[str, Any], bot: Bot) -> Optional[Event]:
        """解析VoceChat事件"""
        try:
            timestamp = payload.get("created_at", 0)

            # 基础事件字段
            event_data = {
                "created_at": timestamp,
                "from_uid": payload.get("from_uid", 0),
                "mid": payload.get("mid", 0),
                "target": payload.get("target", {}),
                "self_uid": bot.user_id,  # 注入机器人自身ID

                "time": datetime.fromtimestamp(timestamp / 1000) if timestamp is not None else datetime.now(),
                "message_id": payload.get("mid", None),  # 兼容性字段
            }
            
            # 根据事件类型创建不同的事件对象
            detail = payload.get("detail", {})
            
            if isinstance(detail, dict):
                event = None

                # 新消息事件
                if detail.get("type") == "normal":
                    event_data["detail"] = detail
                    
                    # 文件消息特殊处理
                    if detail.get("content_type") == "vocechat/file":
                        event = FileMessageEvent.model_validate(event_data)
                    
                    event = MessageNewEvent.model_validate(event_data)

                    self.message_cache.add(event.mid, event.message)
                
                # 回复消息
                elif detail.get("type") == "reply":
                    event_data["detail"] = detail
                    event = MessageNewEvent.model_validate(event_data)
                    reply_id = detail.get("mid", 0)
                    event.reply = Reply(
                        mid= reply_id,
                        message= self.message_cache.get(reply_id)
                    )

                    self.message_cache.add(event.mid, event.message)

                return event
            
            elif isinstance(detail, dict) and detail.get("type") == "reaction":
                reaction_detail = detail.get("detail", {})
                
                # 编辑消息
                if reaction_detail.get("type") == "edit":
                    event_data["detail"] = detail
                    return MessageEditEvent.model_validate(event_data)
                
                # 删除消息
                elif reaction_detail.get("type") == "delete":
                    event_data["detail"] = detail
                    return MessageDeleteEvent.model_validate(event_data)
            
            log("WARNING", f"Unknown event type: {payload}")
            return None
            
        except Exception as e:
            log("ERROR", "Error parsing VoceChat event", e)
            return None