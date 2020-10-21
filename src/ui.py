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

    def title(self, player='', puppet=''):
        if not player:
            self.window.title('Spindizzy')
        elif not puppet:
            self.window.title(f'{player} - Spindizzy')
        else:
            self.window.title(f'{puppet} - {player} - Spindizzy')
