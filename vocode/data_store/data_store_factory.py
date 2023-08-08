import enum
import logging
from vocode.data_store.redis_data_store import RedisTranscriptDataStore


class DataStoreType(enum.Enum):
    MEMORY = 1
    REDIS = 2


class DataStoreFactory:
    def create_data_store(self, type: DataStoreType, logger: logging.Logger):
        if type == DataStoreType.REDIS:
            return RedisTranscriptDataStore(logger=logger)
        else:
            return None
