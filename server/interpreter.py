import asyncio
import ctypes
import io
import logging
import os
import datetime as dt
import pty
import selectors
import socket
import struct
import subprocess
from typing import Optional

libc = ctypes.CDLL("libc.so.6")
logger = logging.getLogger(__name__)

LogAction = int
RECEIVED: LogAction = 1
SENT: LogAction = 2


class Interpreter:

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        conn: socket.socket,
    ):
        self.loop = loop
        self.conn = conn
        self.conn_write_buf = io.BytesIO()
        self.terminal_fd: Optional[int] = None
        self.terminal: Optional[subprocess.Popen] = None
        self._log = open(f"/tmp/aos-server", "a+")
        self._closed: bool = False

    def __del__(self):
        self.close()

    def close(self):
        if self._closed:
            return

        if not self._log.closed:
            self._log.close()

        logger.warning("Closing interpreter...")

        if self.terminal and self.terminal.poll() is None:
            self.terminal.terminate()

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
        self.close()

    async def listener(self):
        conn_fd = self.conn.fileno()
        term_fd = self.terminal_fd

        conn_sel = selectors.DefaultSelector()
        conn_sel.register(conn_fd, selectors.EVENT_READ, data=None)

        term_sel = selectors.DefaultSelector()
        term_sel.register(term_fd, selectors.EVENT_READ, data=None)

        while self.terminal.poll() is None and self.conn.fileno() >= 0:
            await asyncio.sleep(0)

            for key, mask in conn_sel.select(0.001):
                if mask == selectors.EVENT_READ:
                    await self.read_socket()

            for key, mask in term_sel.select(0.001):
                if mask == selectors.EVENT_READ:
                    await self.read_terminal()

    async def read_terminal(self):
        content = os.read(self.terminal_fd, 10240)
        if content:
            await self._send(content)

    async def read_socket(self):
        content = await self._read()
        if content.strip() == b"who":
            await self._send(
                f"A remote terminal. Created by Evgeniy Goncharenko.".encode("utf-8")
            )
            os.write(self.terminal_fd, b"\n")
        else:
            os.write(self.terminal_fd, content)

    async def _read(self) -> bytes:
        header = b''

        while len(header) < 4:
            header += self.conn.recv(4 - len(header))
            if header == b'':
                self.conn.close()
                return b''

        header = struct.unpack("!I", header)
        content_length = header[0]
        content = b''
        while len(content) < content_length:
            content += self.conn.recv(content_length - len(content))
        logger.warning(f"Received {content}...")
        self.log(RECEIVED, content.decode("utf-8"))
        return content

    async def _send(self, content: bytes) -> None:
        content_length = len(content)
        header = struct.pack("!I", content_length)
        message = header + content
        logger.warning(f"Sending {message}...")
        self.conn.sendall(message)
        self.log(SENT, content.decode("utf-8"))

    def log(self, action: LogAction, message: str):
        timestamp = dt.datetime.now().isoformat()
        action_ = "Received" if action == RECEIVED else "Sent"
        self._log.write(f"{action_} at {timestamp}: {message.strip()}\n")
        self._log.flush()
