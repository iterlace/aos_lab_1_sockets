from typing import Optional

import socket
import asyncio


class Client:

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
        self.running = False

    def run(self):
        self.running = True
        self.loop.run_until_complete(self._run())

    async def _run(self):
        while self.running:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.connect((self.host, self.port))
                except ConnectionRefusedError as e:
                    print("Connection refused! Retrying in 2s...")
                    await asyncio.sleep(2)
                    continue

    async def console(self, s):
        while self.running:
            pass

if __name__ == '__main__':
    Client("127.0.0.1", 1028).run()

