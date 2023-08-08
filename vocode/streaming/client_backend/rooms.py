import asyncio
import logging
import aioredis
import os
from fastapi import WebSocket


class BaseRoomsProvider:
    async def initialize(self):
        raise NotImplementedError

    async def terminate(self):
        raise NotImplementedError

    def join_room(self, room_id: str, websocket: WebSocket):
        raise NotImplementedError

    async def publish(self, room_id: str, data):
        raise NotImplementedError


class RedisRoomProvider(BaseRoomsProvider):
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.redis_pool = None

    async def create_redis_connection(self):
        redis_host = os.environ.get("REDIS_HOST", "localhost:6379")

        try:
            self.redis_pool = await aioredis.from_url(
                f"redis://{redis_host}", max_connections=10, encoding="utf-8", decode_responses=True)
        except Exception as e:
            self.logger.error(
                "Error during RedisRoomProvider initialize: %s", e)
            raise

    async def initialize(self):
        await self.create_redis_connection()

    def join_room(self, room_id: str, websocket: WebSocket):
        return asyncio.create_task(self.subscribe(room_id, websocket))

    async def publish(self, room_id: str, data):
        try:
            if self.redis_pool:
                room_id = self.getRoomID(room_id)
                self.logger.debug(f'Publishing to  the Room: {room_id}')
                await self.redis_pool.publish(room_id, data)
        except Exception as e:
            self.logger.error("Error during RedisRoomProvider publish: %s", e)
            raise

    async def terminate(self):
        if self.redis_pool:
            self.logger.debug(f"Terminated room provider")
            await self.redis_pool.close()

    def getRoomID(self, room_id: str):
        return f"channel:room:{room_id}"

    async def subscribe(self, room_id: str, websocket: WebSocket):
        room_id = self.getRoomID(room_id)
        psub = self.redis_pool.pubsub()

        async def reader(channel: aioredis.client.PubSub):
            try:
                while True:
                    async for message in channel.listen():
                        self.logger.debug(
                            f'Received a new message: {room_id}')
                        if message['type'] == "subscribe":
                            continue
                        if message is not None:
                            self.logger.debug(
                                f'Sending the data to all members in the room: {room_id}')
                            await websocket.send_text(message['data'])
            except asyncio.TimeoutError as e:
                self.logger.debug(f'Pubsub timeout received.. {e}')
            except asyncio.CancelledError as e:
                self.logger.debug(f'Cancelled.. {e}')
            except Exception as e:
                self.logger.debug(f'Pubsub exception.. {e}')

        async with psub as p:
            await p.subscribe(room_id)
            await reader(p)  # wait for reader to complete
            self.logger.debug(f'unsubscribing from the room: {room_id}')
            await p.unsubscribe(room_id)

        # closing all open connections
        self.logger.debug(f'closing all open connections: {room_id}')
        await psub.close()
