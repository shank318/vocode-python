import logging
from fastapi import FastAPI
from vocode.data_store.data_store_factory import DataStoreFactory, DataStoreType
from vocode.streaming.client_backend.rooms import RedisRoomProvider
from vocode.streaming.models.synthesizer import AzureSynthesizerConfig
from vocode.streaming.synthesizer.azure_synthesizer import AzureSynthesizer
from vocode.streaming.client_backend.conversation import ConversationRouter

from dotenv import load_dotenv

load_dotenv()

app = FastAPI(docs_url=None)

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

room_provider = None
data_store = None


async def on_startup():
    logger.info('starting fastAPI service..')
    global room_provider
    global data_store

    try:
        # Create room provider and initialize it
        room_provider = RedisRoomProvider(logger)
        await room_provider.initialize()

        # Create data store for transcript
        data_store = DataStoreFactory().create_data_store(DataStoreType.REDIS, logger)

    except Exception as e:
        # Handle the error gracefully, e.g., log the error and exit the application
        logger.error("Error during RedisRoomProvider initialization: %s", e)
        raise

    # ConversationRouter initialization with Redis data store
    conversation_router = ConversationRouter(
        synthesizer_thunk=lambda output_audio_config: AzureSynthesizer(
            AzureSynthesizerConfig.from_output_audio_config(
                output_audio_config, voice_name="en-US-SteffanNeural"
            )
        ),
        data_store=data_store,
        room_provider=room_provider,
        logger=logger,
    )

    # Include the router
    app.include_router(conversation_router.get_router())


async def on_shutdown():
    logger.info('shutting down gracefully..')
    global room_provider
    global data_store

    if data_store is not None:
        data_store.terminate()

    if room_provider is not None:
        await room_provider.terminate()

app.add_event_handler("startup", on_startup)
app.add_event_handler("shutdown", on_shutdown)
