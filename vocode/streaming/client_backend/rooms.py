import asyncio
import logging
import aioredis
import os
import async_timeout
from fastapi import WebSocket


class BaseRoomsProvider:
    def join_room(self, websocket: WebSocket):
        raise NotImplementedError

    def terminate(self):
        raise NotImplementedError

    async def publish(self, data):
        raise NotImplementedError


class RedisRoomProvider(BaseRoomsProvider):
    def __init__(self, logger: logging.Logger, room_id: str):
        self.logger = logger
        self.loop = asyncio.get_event_loop()
        self.room_id = f"channel:room:{room_id}"
        self.disconnect = False
        redis_host = os.environ.get("REDIS_HOST", "redis-container")
        self.redis_pool = aioredis.from_url(
            f"redis://{redis_host}", max_connections=10, encoding="utf-8", decode_responses=True)

    def join_room(self, websocket: WebSocket):
        self.process_task = asyncio.create_task(self.subscribe(websocket))

    def terminate(self):
        self.disconnect = True
        self.process_task.cancel()

    async def subscribe(self, websocket: WebSocket):
        psub = self.redis_pool.pubsub()

        async def reader(channel: aioredis.client.PubSub):
            while True:
                try:
                    message = await channel.get_message(ignore_subscribe_messages=True, timeout=None)
                    if message is not None:
                        self.logger.debug(
                            f'Sending the data to all members in the room: {self.room_id}')
                        await websocket.send_text(message['data'])

                    if self.disconnect is True:
                        self.logger.debug(
                            f'Disconnected pubsub {self.room_id}')
                        break
                except asyncio.TimeoutError as e:
                    self.logger.debug(f'Pubsub timeout received.. {e}')
                    break
                except Exception as e:
                    self.logger.debug(f'Pubsub exception.. {e}')
                    break
                except asyncio.CancelledError:
                    self.logger.debug(f'Cancelled.. {e}')
                    break

        async with psub as p:
            await p.subscribe(self.room_id)
            await reader(p)  # wait for reader to complete
            self.logger.debug(f'unsubscribing from the room: {self.room_id}')
            await p.unsubscribe(self.room_id)

        # closing all open connections
        self.logger.debug(f'closing all open connections: {self.room_id}')
        await psub.close()

    async def publish(self, data):
        if self.disconnect is False:
            self.logger.debug(f'Publishing to  the Room: {self.room_id}')
            await self.redis_pool.publish(self.room_id, data)
