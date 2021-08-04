import socket
import ssl
from datetime import datetime
from threading import Thread
from collections import deque

_context = ssl.create_default_context()

timestamp_fmt = '%d/%m/%Y %H:%M:%S'

class ConnectionClosed(Exception):
    pass

class ConnectionOpen(Exception):
    pass

class Line:
    def __init__(self, message, time=None):
        self.message = message
        self.time = time or format(datetime.now(), timestamp_fmt)

    def __str__(self):
        return f'{self.time}  {self.message}\r\n'

    def __radd__(self, other):
        return Line(other + self.message, self.time)

    def startswith(self, prefix):
        return self.message.startswith(prefix)

    def removeprefix(self, prefix):
        return Line(self.message.removeprefix(prefix), self.time)

class Connection:
    def __init__(self, name, password):
        self.login = (name, password)
        self.isopen = False
        self.buffer = deque()

    def send(self, *messages):
        if not self.isopen:
            raise ConnectionClosed()
        self.socket.sendall(('\r\n'.join(messages) + '\r\n').encode())

    def run(self):
        if not self.isopen:
            raise ConnectionClosed()
        while self.isopen:
            data = bytearray()
            try:
                while True:
                    received = self.socket.recv(4096)
                    if received:
                        data += received
                    else:
                        self.isopen = False
                        break
            except socket.timeout:
                pass
            messages = data.decode().splitlines()
            self.buffer.extend(map(Line, message))
        self.socket.close()

    def receive(self):
        while True:
            try:
                yield self.buffer.popleft()
            except IndexError:
                break

    def open(self):
        if self.isopen:
            raise ConnectionOpen()
        self.isopen = True
        self.socket = _context.wrap_socket(
            socket.create_connection(('muck.spindizzy.org', 7073), 1),
            server_hostname='muck.spindizzy.org'
        )
        self.thread = Thread(target=self.run)
        self.thread.start()
        self.send('connect {} {}'.format(*self.login))

    def close(self):
        if not self.isopen:
            raise ConnectionClosed()
        self.isopen = False
        self.thread.join()
        self.socket.close()
