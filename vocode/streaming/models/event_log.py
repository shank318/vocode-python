import time
from typing import Dict, Optional
from pydantic import BaseModel, Field
from vocode.streaming.models.events import Sender


class EventLog(BaseModel):
    sender: Sender
    timestamp: float = Field(default_factory=time.time)
    
    def to_string(self, include_timestamp: bool = False) -> str:
        raise NotImplementedError


class Message(EventLog):
    text: str
    meta_data: Optional[Dict[str, str]]

    def to_string(self, include_timestamp: bool = False) -> str:
        metadata_str = ', '.join([f"{key}={value}" for key, value in (self.meta_data.items() if self.meta_data else [])])

        if include_timestamp:
            return f"{self.sender.name}: {self.text} {metadata_str} ({self.timestamp})"
        return f"{self.sender.name}: {self.text} {metadata_str}"