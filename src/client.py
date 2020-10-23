from . import config, ui, network, tabs

class Client:
    def __init__(self):
        self.ui = ui.UI()
        self.connections = {}
        self.tabs = {}
        self.active_tab = None
        self.config = config.Config()
        self.characters = config.Characters()
        # Auto-connect players
        for player in self.characters:
            if self.characters.autoconnect(player):
                self.connect(player)

    def get_connection(self, player):
        return self.connections.get(player, None)

    def new_connection(self, player):
        if player not in self.connections:
            password = self.characters.password(player)
            if password:
                self.connections[player] = network.Connection(player, password)
            else:
                pass  # Warn the user the player doesn't exist or has no password set

    def delete_connection(self, player):
        if player in self.connections:
            del self.connections[player]

    def open_connection(self, player):
        conn = self.get_connection(player)
        if conn is None:
            self.new_connection(player)
        elif not conn.isopen:
            conn.open()

    def close_connection(self, player):
        conn = self.get_connection(player)
        if conn is not None and conn.isopen:
            conn.close()

    def get_tab(self, player, puppet=''):
        return self.tabs.get((player, puppet), None)

    def connect(self, player, puppet=''):
        tab = self.get_tab(player, puppet)
        if tab is None:  # Open new tab
            tab = tabs.Tab(self, player, puppet)
            self.tabs[player, puppet] = tab
            self.set_active_tab(tab)
        elif not tab.state().connected:  # Reconnect existing tab
            if not puppet:  # Need a network connection
                self.open_connection(player)
            tab.state(connected=True)
            self.set_active_tab(tab)
        else:
            pass
        # Auto-connect puppets
        if not puppet:
            for puppet in self.characters.puppets(player):
                if self.characters.autoconnect(player, puppet):
                    self.connect(player, puppet)

    def disconnect(self, player, puppet=''):
        tab = self.get_tab(player, puppet)
        if tab is None or not tab.state().connected:
            pass
        else:
            if not puppet:
                self.close_connection(player)
                # Disconnect all puppet tabs
                for tab in self.tabs.values():
                    if tab.player == player and tab.puppet != '':
                        tab.state(connected=False)
            tab.state(connected=False)

    def close(self, player, puppet=''):
        tab = self.get_tab(player, puppet)
        if tab is None:
            pass
        else:
            if tab.state().connected:
                pass  # Warn the player they're connected
            self.disconnect(player, puppet)
            tab.close()
            self.tabs.pop((player, puppet))

    def set_active_tab(self, tab):
        self.active_tab.state(active=False)
        tab.state(active=True)
        self.active_tab = tab

    def send(self, message):
        tab = self.active_tab
        if tab is not None and tab.state().connected:
        # If tab is not connected, ask user if they want to connect
            conn = self.get_connection(tab.player)
            if conn is not None and conn.isopen:
                conn.send(message)

    def receive(self):
        tab = self.active_tab
        if tab is not None:
            conn = self.get_connection(tab.player)
            if conn is not None and conn.isopen:
                return conn.receive()
            else:
                return ''
        else:
            return ''
