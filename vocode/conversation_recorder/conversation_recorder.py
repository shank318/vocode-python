import asyncio
import logging
import os
import wave

from vocode.conversation_recorder.base_recorder import BaseConversationRecorder


class ConversationRecorder(BaseConversationRecorder):
    def __init__(self, logger: logging.Logger, output_file_name: str, desired_chunk_size=300000, sample_rate=48000, channels=1):
        self.logger = logger
        self.sample_rate = sample_rate
        self.channels = channels
        self.conversation_audio = asyncio.Queue()
        self.output_file = output_file_name+".wav"
        self.process_task = None
        self.sample_width = 2
        self.conversation_buffer = b''  # Buffer to store incoming input bytes
        self.desired_chunk_size = desired_chunk_size

    async def add_data_stream(self, input_bytes):
        # Add input bytes to the input buffer
        self.conversation_buffer += input_bytes
        # Process audio when enough data is accumulated in the buffer
        while len(self.conversation_buffer) >= self.desired_chunk_size:
            chunk = self.conversation_buffer[:self.desired_chunk_size]
            self.conversation_buffer = self.conversation_buffer[self.desired_chunk_size:]

            # Process the chunk (e.g., perform audio analysis, apply filters, etc.)
            # Add the processed chunk to the conversation_audio queue
            await self.conversation_audio.put(chunk)

    # async def process_output_bytes(self, output_bytes):
    #     # Add input bytes to the input buffer
    #     self.conversation_buffer += output_bytes
    #     # Process audio when enough data is accumulated in the buffer
    #     while len(self.conversation_buffer) >= self.desired_chunk_size:
    #         chunk = self.conversation_buffer[:self.desired_chunk_size]
    #         self.conversation_buffer = self.conversation_buffer[self.desired_chunk_size:]

    #         # Process the chunk (e.g., perform audio analysis, apply filters, etc.)
    #         # Add the processed chunk to the conversation_audio queue
    #         await self.conversation_audio.put(chunk)

    def start(self):
        self.process_task = asyncio.create_task(self.process())

    async def process(self):
        self.logger.debug('Recording started...')
        while True:
            try:
                item = await self.conversation_audio.get()
                self.save_recording(item)
            except asyncio.CancelledError:
                self.logger.debug('Finishing recording..')
                # Save the rest of the conversation
                if len(self.conversation_buffer) > 0:
                    self.logger.debug(
                        f'Saving final recording before closing..')
                    self.save_recording(self.conversation_buffer)
            except Exception as e:
                self.logger.debug(
                    f"Error occurred while saving the recording: {e}")

    def stop_recording(self):
        self.process_task.cancel()
        self.logger.debug('Recording stopped...')

    def save_recording(self, conversation_audio):
        try:
            # Check if the file exists
            if os.path.exists(self.output_file):
                # Read existing audio data
                with wave.open(self.output_file, 'rb') as existing_wav:
                    existing_frames = existing_wav.readframes(
                        existing_wav.getnframes())
            else:
                existing_frames = b''  # Empty frames if the file doesn't exist

            # Combine existing audio data with new audio data
            combined_frames = existing_frames + conversation_audio

            # Write the updated audio data to a new file
            with wave.open(self.output_file, 'wb') as updated_wav:
                updated_wav.setnchannels(self.channels)
                # 2 bytes (16-bit) per sample
                updated_wav.setsampwidth(self.sample_width)
                updated_wav.setframerate(self.sample_rate)
                updated_wav.writeframes(combined_frames)

            self.logger.debug('Recording saved...')
        except Exception as e:
            self.logger.debug(
                f"Error occurred while saving the recording: {e}")
