from typing import List

from pydantic import BaseModel, ConfigDict, Field


class BotConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    user_id: str
    server: str
    api_key: str


class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")

    vocechat_history_length: int = Field(default=100)
    vocechat_bots: List[BotConfig] = Field(default_factory=list)