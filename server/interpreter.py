from typing import Optional, Union
from asyncio.streams import StreamReader, StreamWriter
import struct
import subprocess
import struct
import pty
import os
import ctypes
import sys
import select
import logging

import socket
import asyncio

from server.helpers import cmd2array

libc = ctypes.CDLL("libc.so.6")
logger = logging.getLogger(__name__)


class Interpreter:

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        reader: StreamReader, writer: StreamWriter
    ):
        self.loop = loop
        self.reader = reader
        self.writer = writer
        self.master_fd = None
        self.slave_fd = None
        self.terminal = None
        self._closed = False

    def init_terminal(self):
        self.master_fd, self.slave_fd = pty.openpty()
        self.terminal = subprocess.Popen(
            ["/bin/bash", "-i"],
            preexec_fn=libc.setsid,
            stdin=self.slave_fd,
            stdout=self.slave_fd,
            stderr=self.slave_fd,
            universal_newlines=True,
        )
        return

    async def run(self):
        self.init_terminal()

        while self.terminal.poll() is None:
            reader_fd = self.reader._transport._sock_fd
            r, _, _ = select.select([self.master_fd, reader_fd], [], [])
            if self.master_fd in r:
                content = os.read(self.master_fd, 10240)
                if content:
                    await self._send(content)
            elif reader_fd in r:
                content = await self._read()
                os.write(self.master_fd, content)
                # FIXME
                # os.read(self.master_fd, len(content)+1)

        self.writer.close()

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
        logger.warning(f"Received {content}...")
        return content

    async def _send(self, content: bytes) -> None:
        content_length = len(content)
        header = struct.pack("!I", content_length)
        message = header + content
        self.writer.write(message)
        logger.warning(f"Sending {message}...")
        await self.writer.drain()
        logger.warning("Sent!")

