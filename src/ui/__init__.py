import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from . import menus

class UI(tk.Tk):
    def __init__(self, client, *args, **kwargs):
        ## Set up window
        super().__init__(*args, **kwargs)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.title()

        # Menus
        self.option_add('*tearOff', False)
        self['menu'] = menus.menubar(self)

        # Output
        output = ScrolledText(self, wrap='word', state='disabled')
        output.grid(column=0, row=0, sticky='nwes')

        # Input
        input = tk.Text(self, height=1, wrap='word')
        input.grid(column=0, row=1, sticky='nwes')

        # Tabbar

        # Final setup
        input.focus()

        self.client = client
        self.output = output
        self.input = input

        self.mainloop()

    def title(self, player='', puppet=''):
        if not player:
            super().title('Spindizzy')
        elif not puppet:
            super().title(f'{player} - Spindizzy')
        else:
            super().title(f'{puppet} - {player} - Spindizzy')
