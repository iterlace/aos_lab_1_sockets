from typing import Optional, Union
import struct
import subprocess
import struct

import socket
import asyncio

from server.helpers import cmd2array


class Interpreter:

    def __init__(self, loop: asyncio.AbstractEventLoop, conn: socket.socket):
        self.loop = loop
        self.conn = conn
        self._closed = False

    def __del__(self):
        self.close()

    def close(self):
        if self._closed:
            return

        self.conn.close()
        self._closed = True

    async def run(self):
        while self.conn:
            message = await self._read()

    async def _execute(self, ):
        pass

    async def _read(self) -> bytes:
        header = b''
        while len(header) < 4:
            header = self.conn.recv(4-len(header))

        header = struct.unpack("!I", header)
        content_length = header[0]
        received = 0
        content = b''

        while received < content_length:
            b = self.conn.recv(1)
            content += b
            received += len(b)

        return content

    async def _send(self, content: bytes) -> None:
        content_length = len(content)
        header = struct.pack("!I", content_length)
        message = header + content
        self.conn.sendall(message)


