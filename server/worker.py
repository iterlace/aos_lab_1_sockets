import logging
from typing import Optional

from asyncio.streams import StreamReader, StreamWriter
import socket
import asyncio

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
        server = self.loop.run_until_complete(
            asyncio.start_server(
                self.handle_connection,
                host=self.host,
                port=self.port,
            )
        )
        try:
            logger.info("Starting at {}:{}...".format(self.host, self.port))
            self.loop.run_forever()
        except Exception as e:
            server.close()
            raise e

        self.loop.run_forever()

    async def handle_connection(self, reader: StreamReader, writer: StreamWriter):
        print("New connection: ")
        await Interpreter(self.loop, reader, writer).run()


if __name__ == '__main__':
    Server("127.0.0.1", 1028).run()

