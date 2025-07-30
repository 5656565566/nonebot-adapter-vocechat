from pydantic import BaseModel, Field
from typing import List

class BotConfig(BaseModel):
    name: str
    user_id: str
    server: str
    api_key: str

class Config(BaseModel):
    message_cache_length: int = 100
    vocechat_bots: List[BotConfig] = Field(default_factory=list)