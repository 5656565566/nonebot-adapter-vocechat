from pydantic import BaseModel, Field
from typing import List

class BotConfig(BaseModel):
    name: str
    user_id: str
    server: str
    api_key: str

class Config(BaseModel):
    vocechat_history_length: int = Field(default=100)
    vocechat_bots: List[BotConfig] = Field(default_factory=list)