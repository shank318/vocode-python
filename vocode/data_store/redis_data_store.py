import logging
import os
from typing import List, Optional
from redis import Redis
from vocode.data_store.base_data_store import Message, TranscriptDataStore


class RedisTranscriptDataStore(TranscriptDataStore):
    conversation_id: str

    def __init__(self, conversation_id: str, logger: Optional[logging.Logger] = None):
        self.conversation_id = conversation_id
        self.logger = logger or logging.getLogger(__name__)

        try:
            self.redis = Redis(host=os.environ.get("REDIS_HOST", "localhost"),
                               port=int(os.environ.get("REDIS_PORT", 6379)),
                               db=0,
                               decode_responses=True,
                               )
        except Exception as e:
            raise RuntimeError("Failed to establish Redis connection") from e

    def getConversationTranscriptCacheKey(self):
        return 'transcript:'+self.conversation_id

    def save_message(self, message: Message):
        self.logger.debug(f"Saving transcript for {self.conversation_id}")
        self.redis.rpush(
            self.getConversationTranscriptCacheKey(), message.json())

    def get_messages(self) -> List[Message]:
        self.logger.debug(f"Getting transcript for {self.conversation_id}")
        transcript = self.redis.lrange(
            self.getConversationTranscriptCacheKey(), 0, -1)
        if transcript:
            messages = [Message.parse_raw(message) for message in transcript]
            return messages
        return []

    def delete_transcript(self):
        self.logger.debug(f"Deleting transcript for {self.conversation_id}")
        self.redis.delete(
            self.getConversationTranscriptCacheKey())

    def terminate(self):
        if self.redis:
            self.logger.debug(f"Terminated redis data store for {self.conversation_id}")
            self.redis.close()
