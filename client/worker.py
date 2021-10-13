from typing import Optional

import sys
import socket
from asyncio.streams import StreamReader, StreamWriter
import os
import select
import struct
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
        self.reader = None
        self.writer = None

    def run(self):
        self.running = True
        self.loop.run_until_complete(self._run())

    async def _run(self):
        try:
            while self.running:
                try:
                    self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
                except ConnectionRefusedError as e:
                    print("Connection refused! Retrying in 2s...")
                    await asyncio.sleep(2)
                    continue

                await self.console()
        except Exception as e:
            self.writer.close()
            raise e
        finally:
            self.writer.close()

    async def console(self):
        print("Connection established!")
        while self.running:
            stdin = sys.stdin.fileno()
            stdout = sys.stdout.fileno()
            reader_fd = self.reader._transport._sock_fd
            r, _, _ = select.select([stdin, reader_fd], [], [])

            if reader_fd in r:
                content = await self._read()
                os.write(stdout, content)
            elif stdin in r:
                content = os.read(stdin, 10240)
                if content:
                    await self._send(content)

        self.running = False
        return

    async def _read(self, timeout=0.5) -> bytes:
        header = b''

        if timeout != -1:
            fut = self.reader.read(1)
            try:
                header += await asyncio.wait_for(fut, timeout=timeout)
            except asyncio.TimeoutError:
                return b''

        header += await self.reader.readexactly(4-len(header))

        header = struct.unpack("!I", header)
        content_length = header[0]
        content = await self.reader.readexactly(content_length)
        return content

    async def _send(self, content: bytes) -> None:
        content_length = len(content)
        header = struct.pack("!I", content_length)
        message = header + content
        self.writer.write(message)
        await self.writer.drain()


if __name__ == '__main__':
    Client("127.0.0.1", 1028).run()

