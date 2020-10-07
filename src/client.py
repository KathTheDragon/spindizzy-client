from . import ui, network

class Client:
    def __init__(self):
        self.window, self.output, self.input, self.tabbar = ui.create()
        self.connections = {}
        self.active_tab = None
        self.set_title()

    def set_title(self, player='', puppet=''):
        if not player:
            self.window.title('Spindizzy')
        elif not puppet:
            self.window.title(f'{player} - Spindizzy')
        else:
            self.window.title(f'{puppet} - {player} - Spindizzy')

    def get_connection(self, player):
        return self.connections.get(player, None)

    def new_connection(self, player, password):
        if player not in self.connections:
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
        if self.active_conn.isopen:
            self.active_conn.send(message)

    def receive(self):
        if self.active_conn.isopen:
            return self.active_conn.receive()
        else:
            return ''

    def set_active_tab(self, tab):
        if self.active_tab is not None:
            self.active_tab.configure(relief='raised')
        tab.configure(relief='sunken')
        self.active_tab = tab
        self.set_title(tab.player, tab.puppet)

    def add_tab(self, player, puppet=''):
        ui.add_tab(self, player, puppet)
