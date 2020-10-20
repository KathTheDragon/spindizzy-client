import tkinter as tk
from tkinter import ttk

class UI:
    def __init__(self):
        window = tk.Tk()
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)
        self.title()

        # Menus
        window.option_add('*tearOff', False)
        menubar = tk.Menu(window)
        window['menu'] = menubar
        menu_file = tk.Menu(menubar)
        menubar.add_cascade(menu=menu_file, label='File')

        # Output
        output = tk.Text(window, wrap='word', state='disabled')
        output_scroll = ttk.Scrollbar(window, orient=tk.VERTICAL, command=output.yview)
        output.configure(yscrollcommand=output_scroll.set)
        output.grid(column=0, row=0, sticky='nwes')
        output_scroll.grid(column=1, row=0, sticky='nwes')

        # Input
        input = tk.Text(window, height=1, wrap='word')
        input.grid(column=0, row=1, columnspan=2, sticky='nwes')

        # Tabbar
        tabbar = ttk.Frame(window, height=16)
        tabbar.grid(column=0, row=2, columnspan=2, sticky='nwes')

        # Final setup
        input.focus()

        self.window = window
        self.output = output
        self.input = input
        self.tabbar = tabbar
        self.active_tab = None

    def title(self, player='', puppet=''):
        if not player:
            self.window.title('Spindizzy')
        elif not puppet:
            self.window.title(f'{player} - Spindizzy')
        else:
            self.window.title(f'{puppet} - {player} - Spindizzy')

    def add_tab(self, player, puppet=''):
        tab = ttk.Frame(self.tabbar, padding=(5, 1), borderwidth=2, relief='raised')
        tab.player = player
        tab.puppet = puppet
        tab.grid(column=len(self.tabbar.grid_slaves()), row=0)
        if puppet:
            label = ttk.Label(tab, text=f'{puppet} - {player}')
        else:
            label = ttk.Label(tab, text=player)
        label.grid()

        tab.bind('<1>', lambda e: self.set_active_tab(tab))
        label.bind('<1>', lambda e: self.set_active_tab(tab))

    def set_active_tab(self, tab):
        if self.active_tab is not None:
            self.active_tab.configure(relief='raised')
        tab.configure(relief='sunken')
        self.active_tab = tab
        self.title(tab.player, tab.puppet)
