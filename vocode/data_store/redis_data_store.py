import logging
import os
from typing import List, Optional
from redis import Redis
from vocode.data_store.base_data_store import Message, TranscriptDataStore


class RedisTranscriptDataStore(TranscriptDataStore):
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

        try:
            self.redis = Redis(host=os.environ.get("REDIS_HOST", "localhost"),
                               port=int(os.environ.get("REDIS_PORT", 6379)),
                               db=0,
                               decode_responses=True,
                               )
        except Exception as e:
            raise RuntimeError("Failed to establish Redis connection") from e

    def getConversationTranscriptCacheKey(self, conversation_id: str):
        return 'transcript:'+conversation_id

    def save_message(self, conversation_id: str, message: Message):
        self.logger.debug(f"Saving transcript for {conversation_id}")
        self.redis.rpush(
            self.getConversationTranscriptCacheKey(conversation_id), message.json())

    def get_messages(self, conversation_id: str) -> List[Message]:
        self.logger.debug(f"Getting transcript for {conversation_id}")
        transcript = self.redis.lrange(
            self.getConversationTranscriptCacheKey(conversation_id), 0, -1)
        if transcript:
            messages = [Message.parse_raw(message) for message in transcript]
            return messages
        return []

    def delete_transcript(self, conversation_id: str):
        self.logger.debug(f"Deleting transcript for {conversation_id}")
        self.redis.delete(
            self.getConversationTranscriptCacheKey(conversation_id))

    def terminate(self):
        if self.redis:
            self.logger.debug(
                f"Terminated redis data store")
            self.redis.close()
