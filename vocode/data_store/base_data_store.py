from typing import List
from vocode.streaming.models.event_log import Message

class TranscriptDataStore:
    def save_message(self, message: Message):
        raise NotImplementedError

    def get_messages(self) -> List[Message]:
        raise NotImplementedError

    def delete_message(self):
        raise NotImplementedError

    def terminate(self):
        raise NotImplementedError