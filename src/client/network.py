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

    def send(self, message):
        if not self.isopen:
            raise ConnectionClosed()
        if not message.endswith('\r\n'):
            message += '\r\n'
        self.sent.append(message)
        self.socket.sendall(message.encode())

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
            message = data.decode()
            self.received.append(message)
            return message

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

