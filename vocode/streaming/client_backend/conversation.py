import logging
from typing import Callable, Dict, Optional
import typing

from fastapi import APIRouter, WebSocket
from vocode.data_store.redis_data_store import RedisTranscriptDataStore
from vocode.streaming.agent.base_agent import BaseAgent
from vocode.streaming.agent.chat_gpt_agent import ChatGPTAgent
from vocode.streaming.models.agent import ChatGPTAgentConfig
from vocode.streaming.models.audio_encoding import AudioEncoding
from vocode.streaming.models.client_backend import InputAudioConfig, OutputAudioConfig
from vocode.streaming.models.message import BaseMessage
from vocode.streaming.models.synthesizer import AzureSynthesizerConfig, SynthesizerConfig
from vocode.streaming.models.transcriber import (
    DeepgramTranscriberConfig,
    PunctuationEndpointingConfig,
    TranscriberConfig,
)
from vocode.streaming.models.websocket import (
    AudioConfigStartMessage,
    AudioMessage,
    ReadyMessage,
    StartMessage,
    WebSocketMessage,
    WebSocketMessageType,
)

from vocode.streaming.output_device.websocket_output_device import WebsocketOutputDevice
from vocode.streaming.streaming_conversation import StreamingConversation
from vocode.streaming.synthesizer.azure_synthesizer import AzureSynthesizer
from vocode.streaming.synthesizer.base_synthesizer import BaseSynthesizer
from vocode.streaming.transcriber.base_transcriber import BaseTranscriber
from vocode.streaming.transcriber.deepgram_transcriber import DeepgramTranscriber
from vocode.streaming.utils.base_router import BaseRouter

from vocode.streaming.models.events import Event, EventType
from vocode.streaming.models.transcript import TranscriptEvent
from vocode.streaming.utils import events_manager


class ConversationRouter(BaseRouter):
    def __init__(
        self,
        transcriber_thunk: Callable[
            [TranscriberConfig], BaseTranscriber
        ] = lambda transcriber_config: DeepgramTranscriber(
            transcriber_config
        ),
        synthesizer_thunk: Callable[
            [SynthesizerConfig], BaseSynthesizer
        ] = lambda synthesizer_config: AzureSynthesizer(
            synthesizer_config
        ),
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__()
        self.transcriber_thunk = transcriber_thunk
        self.synthesizer_thunk = synthesizer_thunk
        self.logger = logger or logging.getLogger(__name__)
        self.router = APIRouter()
        self.router.websocket("/conversation")(self.conversation)

    def get_conversation(
        self,
        output_device: WebsocketOutputDevice,
        start_message: StartMessage,
        query_params: Dict[str, str],
    ) -> StreamingConversation:
        transcriber = self.transcriber_thunk(start_message.transcriber_config)
        synthesizer = self.synthesizer_thunk(start_message.synthesizer_config)
        synthesizer.synthesizer_config.should_encode_as_wav = True

        self.agent = ChatGPTAgent(
            logger=self.logger,
            agent_config=typing.cast(
                ChatGPTAgentConfig, start_message.agent_config)
        )

        return StreamingConversation(
            output_device=output_device,
            transcriber=transcriber,
            agent=self.agent,
            synthesizer=synthesizer,
            query_params=query_params,
            conversation_id=start_message.conversation_id,
            transcript_data_store=RedisTranscriptDataStore(
                conversation_id=start_message.conversation_id,
                logger=self.logger,
            ),
            # events_manager=TranscriptEventManager(
            #     output_device, self.logger) if start_message.subscribe_transcript else None,
            logger=self.logger,
        )

    async def conversation(self, websocket: WebSocket):
        await websocket.accept()
        start_message: StartMessage = StartMessage.parse_obj(
            await websocket.receive_json()
        )

        query_params = dict(websocket.query_params)

        query_params_str = ', '.join([f"{key}={value}" for key, value in (
            query_params.items() if query_params else [])])
        self.logger.debug(
            f"Conversation started id: {start_message.conversation_id}, query_params: {query_params_str}")

        output_device = WebsocketOutputDevice(
            websocket,
            start_message.transcriber_config.sampling_rate,
            start_message.synthesizer_config.audio_encoding,
        )

        conversation = self.get_conversation(
            output_device, start_message, query_params)
        await conversation.start(lambda: websocket.send_text(ReadyMessage().json()))
        while conversation.is_active():
            message: WebSocketMessage = WebSocketMessage.parse_obj(
                await websocket.receive_json()
            )
            if message.type == WebSocketMessageType.STOP:
                break
            audio_message = typing.cast(AudioMessage, message)
            conversation.receive_audio(audio_message.get_bytes())
        output_device.mark_closed()
        conversation.terminate()

    def get_router(self) -> APIRouter:
        return self.router


class TranscriptEventManager(events_manager.EventsManager):
    def __init__(self, output_device: WebsocketOutputDevice, logger: Optional[logging.Logger] = None):
        super().__init__(subscriptions=[EventType.TRANSCRIPT])
        self.output_device = output_device
        self.logger = logger or logging.getLogger(__name__)

    def handle_event(self, event: Event):
        if event.type == EventType.TRANSCRIPT:
            transcript_event = typing.cast(TranscriptEvent, event)
            self.output_device.consume_transcript(transcript_event)
            # self.logger.debug(event.dict())

    def restart(self, output_device: WebsocketOutputDevice):
        self.output_device = output_device
