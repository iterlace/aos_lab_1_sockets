import io
from typing import Optional, Union
import selectors
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
import time
from concurrent.futures.thread import ThreadPoolExecutor

import socket
import asyncio

libc = ctypes.CDLL("libc.so.6")
logger = logging.getLogger(__name__)


class Interpreter:

    def __init__(
        self,
        loop: Optional[asyncio.AbstractEventLoop],
        conn: socket.socket,
    ):
        if loop is None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        self.loop = loop
        self.conn = conn
        self.conn_write_buf = io.BytesIO()
        self.terminal_fd: Optional[int] = None
        self.terminal: Optional[subprocess.Popen] = None
        self._closed: bool = False

    def __del__(self):
        self.close()

    def close(self):
        if self._closed:
            return

        if self.terminal and self.terminal.poll() is None:
            self.terminal.terminate()

        # self.conn.close()
        self._closed = True

    def init_terminal(self):
        self.terminal_fd, slave_fd = pty.openpty()
        self.terminal = subprocess.Popen(
            ["/bin/bash", "-i"],
            preexec_fn=libc.setsid,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            universal_newlines=True,
        )
        return

    async def run(self):
        self.init_terminal()

        await self.listener()

        # self.loop.add_reader(
        #     self.conn.fileno(),
        #     lambda *args: self.loop.create_task(self.read_socket()),
        # )
        # self.loop.add_reader(
        #     self.terminal_fd,
        #     lambda *args: self.loop.create_task(self.read_terminal()),
        # )

        # while self.terminal.poll() is None:
        #     await asyncio.sleep(0.1)

        self.close()

    async def listener(self):
        conn_fd = self.conn.fileno()
        term_fd = self.terminal_fd

        conn_sel = selectors.DefaultSelector()
        conn_sel.register(conn_fd, selectors.EVENT_READ, data=None)

        term_sel = selectors.DefaultSelector()
        term_sel.register(term_fd, selectors.EVENT_READ, data=None)

        while self.terminal.poll() is None:
            await asyncio.sleep(0)

            for key, mask in conn_sel.select(0.01):
                await self.read_socket()

            for key, mask in term_sel.select(0.01):
                await self.read_terminal()

            # r, _, _ = self.selector.select([self.terminal_fd, conn_fd], [], [], timeout=0.1)
            # if self.terminal_fd in r:
            #     await self.read_terminal()
            # elif conn_fd in r:
            #     await self.read_socket()

    async def read_terminal(self):
        content = os.read(self.terminal_fd, 10240)
        if content:
            await self._send(content)

    async def read_socket(self):
        content = await self._read()
        os.write(self.terminal_fd, content)

    async def _read(self, timeout=0.5) -> bytes:
        logger.warning("Reading from socket...")
        header = b''

        while len(header) < 4:
            header = self.conn.recv(4-len(header))

        header = struct.unpack("!I", header)
        content_length = header[0]
        content = b''
        while len(content) < content_length:
            content += self.conn.recv(content_length-len(content))
        logger.warning(f"Received {content}...")
        return content

    async def _send(self, content: bytes) -> None:
        content_length = len(content)
        header = struct.pack("!I", content_length)
        message = header + content
        logger.warning(f"Sending {message}...")
        self.conn.sendall(message)
        logger.warning("Sent!")

