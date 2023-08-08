from typing import List
from vocode.streaming.models.event_log import Message

class TranscriptDataStore:
    def save_message(self, conversation_id: str, message: Message):
        raise NotImplementedError

    def get_messages(self, conversation_id: str) -> List[Message]:
        raise NotImplementedError

    def delete_message(self):
        raise NotImplementedError

    def terminate(self):
        raise NotImplementedError