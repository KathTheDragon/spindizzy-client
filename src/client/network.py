import socket
import ssl
from threading import Thread
from collections import deque

_context = ssl.create_default_context()

class ConnectionClosed:
    pass

class ConnectionOpen:
    pass

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
            # Timestamp
            self.buffer.extend(messages)
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
