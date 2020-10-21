import tkinter as tk
from tkinter import ttk
from collections import namedtuple

# Should probably be in ui.py
def tabwidget(client, tab, player, puppet):
    tabbar = client.ui.tabbar
    widget = ttk.Frame(tabbar, padding=(5, 1), borderwidth=2, relief='raised')
    widget.grid(column=len(tabbar.grid_slaves()), row=0)
    if puppet:
        label = ttk.Label(widget, text=f'{puppet} - {player}')
    else:
        label = ttk.Label(widget, text=player)
    label.grid()

    widget.bind('<1>', lambda e: client.set_active_tab(tab))
    label.bind('<1>', lambda e: client.set_active_tab(tab))

    tabcontext = tk.Menu(widget)
    tabcontext.add_command(label='Disconnect', command=lambda: client.disconnect(player, puppet))
    tabcontext.add_command(label='Reconnect', command=lambda: client.connect(player, puppet))
    tabcontext.add_separator()
    tabcontext.add_command(label='Close', command=lambda: client.close(player, puppet))
    if (widget.tk.call('tk', 'windowingsystem')=='aqua'):
        widget.bind('<2>', lambda e: tabcontext.post(e.x_root, e.y_root))
        widget.bind('<Control-1>', lambda e: tabcontext.post(e.x_root, e.y_root))
    else:
        widget.bind('<3>', lambda e: tabcontext.post(e.x_root, e.y_root))

    return widget

TabState = namedtuple('TabState', 'active connected')

class Tab:
    def __init__(self, client, player, puppet=''):
        self.player = player
        self.puppet = puppet
        self.active = False
        self.connected = True
        self.sent = []
        self.received = []
        self.widget = tabwidget(client, self, player, puppet)

    def state(self, active=None, connected=None):
        if active is not None:
            self.active = active
            if active:
                self.widget.configure(relief='sunken')
            else:
                self.widget.configure(relief='raised')
        if connected is not None:
            self.connected = connected
            # To-do: figure out appearances here
            if connected:
                pass
            else:
                pass
        return TabState(self.active, self.connected)

    def close(self):
        self.widget.grid_forget()
