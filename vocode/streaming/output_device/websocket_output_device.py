from __future__ import annotations

import asyncio
from typing import Optional
from vocode.conversation_recorder.base_recorder import BaseConversationRecorder
from vocode.streaming.client_backend.rooms import BaseRoomsProvider
from vocode.streaming.models.audio_encoding import AudioEncoding
from vocode.streaming.output_device.base_output_device import BaseOutputDevice
from vocode.streaming.models.websocket import AudioMessage
from vocode.streaming.models.websocket import TranscriptMessage
from vocode.streaming.models.transcript import TranscriptEvent


class WebsocketOutputDevice(BaseOutputDevice):
    def __init__(
        self, room_provider: BaseRoomsProvider, sampling_rate: int, audio_encoding: AudioEncoding, conversation_recorder: Optional[BaseConversationRecorder] = None
    ):
        super().__init__(sampling_rate, audio_encoding)
        self.room_provider = room_provider
        self.active = False
        self.conversation_recorder = conversation_recorder
        self.queue: asyncio.Queue[str] = asyncio.Queue()

    def start(self):
        self.active = True
        self.process_task = asyncio.create_task(self.process())

    def mark_closed(self):
        self.active = False

    async def process(self):
        while self.active:
            message = await self.queue.get()
            await self.room_provider.publish(message)

    def consume_nonblocking(self, chunk: bytes):
        if self.active:
            audio_message = AudioMessage.from_bytes(chunk)
            # send data for recording
            if self.conversation_recorder is not None:
                asyncio.ensure_future(
                    self.conversation_recorder.add_data_stream(chunk))
            self.queue.put_nowait(audio_message.json())

    def consume_transcript(self, event: TranscriptEvent):
        if self.active:
            transcript_message = TranscriptMessage.from_event(event)
            self.queue.put_nowait(transcript_message.json())

    def terminate(self):
        self.process_task.cancel()
