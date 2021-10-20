import uuid
from typing import Optional, Union
import datetime as dt
import logging

import sys
import socket
from asyncio.streams import StreamReader, StreamWriter
import os
import select
import struct
import asyncio

LogAction = int
RECEIVED: LogAction = 1
SENT: LogAction = 2


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
        self.running: bool = False
        self.reader: Optional[StreamReader] = None
        self.writer: Optional[StreamWriter] = None
        self._log = open(f"/tmp/aos-client", "a+")

    def __del__(self):
        if not self._log.closed:
            self._log.close()

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
                if self.reader.at_eof():
                    self.running = False
                    continue
                content = await self._read()
                os.write(stdout, content)
            elif stdin in r:
                content = os.read(stdin, 10240)
                if content:
                    await self._send(content)

        self.running = False
        return

    async def _read(self, timeout=0.5) -> bytes:
        assert timeout >= 0

        header = b''

        try:
            fut = self.reader.read(1)
            header += await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            return b''

        if self.reader.at_eof():
            self.running = False
            return b''

        header += await self.reader.readexactly(4-len(header))

        header = struct.unpack("!I", header)
        content_length = header[0]
        content = await self.reader.readexactly(content_length)
        self.log(RECEIVED, content)
        return content

    async def _send(self, content: bytes) -> None:
        content_length = len(content)
        header = struct.pack("!I", content_length)
        message = header + content
        self.writer.write(message)
        await self.writer.drain()
        self.log(SENT, content)

    def log(self, action: LogAction, message: Union[bytes, str]):
        if isinstance(message, bytes):
            try:
                message = message.decode("utf-8")
            except UnicodeDecodeError:
                return

        timestamp = dt.datetime.now().isoformat()
        action_ = "Received" if action == RECEIVED else "Sent"
        self._log.write(f"{action_} at {timestamp}: {message.strip()}\n")
        self._log.flush()


if __name__ == '__main__':
    Client("127.0.0.1", 1028).run()

