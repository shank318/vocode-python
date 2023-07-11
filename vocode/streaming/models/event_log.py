from typing import Dict, Optional
from vocode.streaming.models.events import Sender
from vocode.streaming.models.model import BaseModel


class EventLog(BaseModel):
    sender: Sender
    timestamp: float

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