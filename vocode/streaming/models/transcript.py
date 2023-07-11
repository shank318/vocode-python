import time
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
from vocode.data_store.base_data_store import TranscriptDataStore
from vocode.streaming.models.actions import ActionOutput, ActionType
from vocode.streaming.models.event_log import EventLog, Message
from vocode.streaming.models.events import Sender, Event, EventType
from vocode.streaming.utils.events_manager import EventsManager

class Action(EventLog):
    sender: Sender = Sender.ACTION_WORKER
    action_type: ActionType
    action_output: ActionOutput

    def to_string(self, include_timestamp: bool = False):
        if include_timestamp:
            return (
                f"{Sender.ACTION_WORKER.name}: {self.action_output} ({self.timestamp})"
            )
        return f"{Sender.ACTION_WORKER.name}: {self.action_output}"


class Transcript(BaseModel):
    event_logs: List[EventLog] = []
    start_time: float = Field(default_factory=time.time)
    meta_data: Dict[str, str] = {}
    events_manager: Optional[EventsManager] = None
    data_store: Optional[TranscriptDataStore] = None

    class Config:
        arbitrary_types_allowed = True

    def attach_events_manager(self, events_manager: EventsManager):
        self.events_manager = events_manager

    def add_meta_data(self, key: str, value: str):
        if self.meta_data is None:
            self.meta_data = {}
        self.meta_data[key] = value

    def attach_data_store(self, data_store: TranscriptDataStore):
        self.data_store = data_store

    def to_string(self, include_timestamps: bool = False) -> str:
        return "\n".join(
            event.to_string(include_timestamp=include_timestamps)
            for event in self.event_logs
        )

    def get_messages(self) -> List[Message]:
        if self.data_store is not None:
            return self.data_store.get_messages()
        else:
            return self.event_logs

    def add_message(
        self,
        text: str,
        sender: Sender,
        conversation_id: str,
    ):
        timestamp = time.time()
        message = Message(text=text, sender=sender, timestamp=timestamp)
        message.meta_data = self.meta_data
        
        if self.data_store is not None:
            self.data_store.save_message(message)
        else:
            self.event_logs.append(message)

        if self.events_manager is not None:
            self.events_manager.publish_event(
                TranscriptEvent(
                    text=text,
                    sender=sender,
                    timestamp=time.time(),
                    conversation_id=conversation_id,
                )
            )

    def add_human_message(self, text: str, conversation_id: str):
        self.add_message(
            text=text,
            sender=Sender.HUMAN,
            conversation_id=conversation_id,
        )

    def add_bot_message(self, text: str, conversation_id: str):
        self.add_message(
            text=text,
            sender=Sender.BOT,
            conversation_id=conversation_id,
        )

    def add_action_log(self, action_output: ActionOutput, conversation_id: str):
        timestamp = time.time()
        self.event_logs.append(
            Action(
                action_output=action_output,
                action_type=action_output.action_type,
                timestamp=timestamp,
            )
        )
        # TODO: add to event manager


class TranscriptEvent(Event, type=EventType.TRANSCRIPT):
    text: str
    sender: Sender
    timestamp: float

    def to_string(self, include_timestamp: bool = False) -> str:
        if include_timestamp:
            return f"{self.sender.name}: {self.text} ({self.timestamp})"
        return f"{self.sender.name}: {self.text}"


class TranscriptCompleteEvent(Event, type=EventType.TRANSCRIPT_COMPLETE):
    transcript: Transcript
