import time
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
from vocode.data_store.base_data_store import TranscriptDataStore
from vocode.streaming.models.actions import ActionOutput, ActionInput
from vocode.streaming.models.event_log import EventLog, Message
from vocode.streaming.models.events import ActionEvent, Sender, Event, EventType
from vocode.streaming.utils.events_manager import EventsManager


class ActionStart(EventLog):
    sender: Sender = Sender.ACTION_WORKER
    action_type: str
    action_input: ActionInput

    def to_string(self, include_timestamp: bool = False):
        if include_timestamp:
            return (
                f"{Sender.ACTION_WORKER.name}: {self.action_input} ({self.timestamp})"
            )
        return f"{Sender.ACTION_WORKER.name}: {self.action_input}"


class ActionFinish(EventLog):
    sender: Sender = Sender.ACTION_WORKER
    action_type: str
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

    def maybe_publish_transcript_event_from_message(
        self, message: Message, conversation_id: str
    ):
        if self.events_manager is not None:
            self.events_manager.publish_event(
                TranscriptEvent(
                    text=message.text,
                    sender=message.sender,
                    timestamp=message.timestamp,
                    conversation_id=conversation_id,
                )
            )

    def get_messages(self) -> List[Message]:
        if self.data_store is not None:
            return self.data_store.get_messages()
        else:
            return self.event_logs

    def add_message_from_props(
        self,
        text: str,
        sender: Sender,
        conversation_id: str,
        publish_to_events_manager: bool = True,
    ):
        timestamp = time.time()
        message = Message(text=text, sender=sender, timestamp=timestamp)
        self.event_logs.append(message)
        if publish_to_events_manager:
            self.maybe_publish_transcript_event_from_message(
                message=message, conversation_id=conversation_id
            )

    def add_message(
        self,
        message: Message,
        conversation_id: str,
        publish_to_events_manager: bool = True,
    ):
        self.event_logs.append(message)
        if publish_to_events_manager:
            self.maybe_publish_transcript_event_from_message(
                message=message, conversation_id=conversation_id
            )

    def add_human_message(self, text: str, conversation_id: str):
        self.add_message_from_props(
            text=text,
            sender=Sender.HUMAN,
            conversation_id=conversation_id,
        )

    def add_bot_message(self, text: str, conversation_id: str):
        self.add_message_from_props(
            text=text,
            sender=Sender.BOT,
            conversation_id=conversation_id,
        )

    def get_last_user_message(self):
        for idx, message in enumerate(self.event_logs[::-1]):
            if message.sender == Sender.HUMAN:
                return -1 * (idx + 1), message.to_string()

    def add_action_start_log(self, action_input: ActionInput, conversation_id: str):
        timestamp = time.time()
        self.event_logs.append(
            ActionStart(
                action_input=action_input,
                action_type=action_input.action_config.type,
                timestamp=timestamp,
            )
        )
        if self.events_manager is not None:
            self.events_manager.publish_event(
                ActionEvent(
                    action_input=action_input.dict(),
                    conversation_id=conversation_id,
                )
            )

    def add_action_finish_log(
        self,
        action_input: ActionInput,
        action_output: ActionOutput,
        conversation_id: str,
    ):
        timestamp = time.time()
        self.event_logs.append(
            ActionFinish(
                action_output=action_output,
                action_type=action_output.action_type,
                timestamp=timestamp,
            )
        )
        if self.events_manager is not None:
            self.events_manager.publish_event(
                ActionEvent(
                    action_input=action_input.dict(),
                    action_output=action_output.dict(),
                    conversation_id=conversation_id,
                )
            )

    def update_last_bot_message_on_cut_off(self, text: str):
        # TODO: figure out what to do for the event
        for event_log in reversed(self.event_logs):
            if isinstance(event_log, Message) and event_log.sender == Sender.BOT:
                event_log.text = text
                break


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
