from typing import List

from pydantic import BaseModel, Field


class BotConfig(BaseModel):
    name: str | None = None
    user_id: str
    server: str
    api_key: str


class Config(BaseModel):
    vocechat_history_length: int = Field(default=100)
    vocechat_bots: List[BotConfig] = Field(default_factory=list)