from pydantic import BaseModel, Field
from typing import List

class BotConfig(BaseModel):
    name: str
    server: str
    api_key: str

class Config(BaseModel):
    vocechat_bots: List[BotConfig] = Field(default_factory=list)