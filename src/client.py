from . import ui, network

class Client:
    def __init__(self, config):
        self.ui = ui.UI()
        self.connections = {}
        self.config = config

    def get_connection(self, player):
        return self.connections.get(player, None)

    def new_connection(self, player):
        if player not in self.connections:
            password = self.config.password(player)
            self.connections[player] = network.Connection(player, password)

    def delete_connection(self, player):
        if player in self.connections:
            del self.connections[player]

    def open_connection(self, player):
        conn = self.get_connection(player)
        if conn is not None and not conn.isopen:
            conn.open()

    def close_connection(self, player):
        conn = self.get_connection(player)
        if conn is not None and conn.isopen:
            conn.close()

    def send(self, message):
        tab = self.ui.active_tab
        if tab is not None:
            conn = self.get_connection(tab.player)
            if conn is not None and conn.isopen:
                conn.send(message)

    def receive(self):
        tab = self.ui.active_tab
        if tab is not None:
            conn = self.get_connection(tab.player)
            if conn is not None and conn.isopen:
                return conn.receive()
            else:
                return ''
        else:
            return ''
