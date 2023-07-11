import logging
from threading import Thread
import time
from fastapi import FastAPI
from vocode.streaming.agent.base_agent import TranscriptionAgentInput

from vocode.streaming.models.agent import ChatGPTAgentConfig
from vocode.streaming.models.synthesizer import AzureSynthesizerConfig
from vocode.streaming.synthesizer.azure_synthesizer import AzureSynthesizer

from vocode.streaming.agent.chat_gpt_agent import ChatGPTAgent
from vocode.streaming.client_backend.conversation import ConversationRouter
from vocode.streaming.models.message import BaseMessage

from dotenv import load_dotenv

from vocode.streaming.transcriber.base_transcriber import Transcription

load_dotenv()

app = FastAPI(docs_url=None)

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

conversation_router = ConversationRouter(
    synthesizer_thunk=lambda output_audio_config: AzureSynthesizer(
        AzureSynthesizerConfig.from_output_audio_config(
            output_audio_config, voice_name="en-US-SteffanNeural"
        )
    ),
    logger=logger,
)

app.include_router(conversation_router.get_router())