import socket
import ssl

_context = ssl.create_default_context()

class ConnectionClosed:
    pass

class ConnectionOpen:
    pass

class Connection:
    def __init__(self, name, password):
        self.login = (name, password)
        self.isopen = False
        self.sent = []
        self.received = []

    def send(self, *messages):
        if not self.isopen:
            raise ConnectionClosed()
        self.sent.extend(messages)
        self.socket.sendall(('\r\n'.join(messages) + '\r\n').encode())

    def receive(self):
        if not self.isopen:
            raise ConnectionClosed()
        data = bytearray()
        try:
            while True:
                received = self.socket.recv(4096)
                if received:
                    data += received
                else:
                    self.close()
                    break
        except socket.timeout:
            pass
        finally:
            messages = data.decode().splitlines()
            self.received.extend(messages)
            return messages

    def open(self):
        if self.isopen:
            raise ConnectionOpen()
        self.isopen = True
        self.socket = _context.wrap_socket(
            socket.create_connection(('muck.spindizzy.org', 7073), 1),
            server_hostname='muck.spindizzy.org'
        )
        self.send('connect {} {}'.format(*self.login))

    def close(self):
        if not self.isopen:
            raise ConnectionClosed()
        self.isopen = False
        self.socket.close()
