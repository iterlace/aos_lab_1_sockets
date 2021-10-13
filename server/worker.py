import asyncio
import logging
import socket
from typing import Optional

from interpreter import Interpreter

logger = logging.getLogger(__name__)


class Server:

    def __init__(
        self,
        host: str,
        port: int,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        if loop is None:
            loop = asyncio.get_event_loop()

        self.host = host
        self.port = port
        self.loop = loop

    def run(self):
        self.loop.run_until_complete(self.listen())

    async def listen(self):
        try:
            logger.info("Starting at {}:{}...".format(self.host, self.port))
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self.host, self.port))
                s.listen()
                s.setblocking(False)
                while True:
                    conn, addr = await self.loop.sock_accept(s)
                    conn.setblocking(False)
                    self.loop.create_task(self.handle_connection(conn))
        except Exception as e:
            raise e

    async def handle_connection(self, conn: socket.socket):
        print("New connection")
        try:
            await Interpreter(self.loop, conn).run()
        except Exception as e:
            conn.close()
            raise e
        finally:
            conn.close()


if __name__ == '__main__':
    Server("127.0.0.1", 1028).run()
