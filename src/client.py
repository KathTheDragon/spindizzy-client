from . import ui, network

class Client:
    def __init__(self):
        self.window, self.output, self.input, self.tabbar = ui.create()
        self.set_title()
        self.connections = []
        self.active_conn = None

    def set_title(self, player='', puppet=''):
        if not player:
            self.window.title('Spindizzy')
        elif not puppet:
            self.window.title(f'{player} - Spindizzy')
        else:
            self.window.title(f'{puppet} - {player} - Spindizzy')

    def get_connection(self, index):
        try:
            return self.connections[index]
        except IndexError:
            return None

    def set_active_conn(self, index):
        conn = self.get_connection(index)
        if conn is not None:
            self.active_conn = conn

    def clear_active_conn(self):
        self.active_conn = None

    def new_connection(self, player='', password=''):
        index = len(self.connections)
        self.connections.append(network.Connection(player, password))
        self.set_active_conn(-1)
        return index

    def open_connection(self, index):
        conn = self.get_connection(index)
        if conn is not None and not conn.isopen:
            conn.open()

    def close_connection(self, index):
        conn = self.get_connection(index)
        if conn is not None and conn.isopen:
            conn.close()

    def delete_connection(self, index):
        try:
            self.connections[index] = None
        except IndexError:
            pass

    def send(self, message):
        if self.active_conn.isopen:
            self.active_conn.send(message)

    def receive(self):
        if self.active_conn.isopen:
            return self.active_conn.receive()
        else:
            return ''
