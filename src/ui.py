import tkinter as tk
from tkinter import ttk

def create():
    # Set up window
    window = tk.Tk()
    create_menus(window)

    # Create widgets
    output = tk.Text(window, wrap='word', state='disabled')
    output_scroll = ttk.Scrollbar(window, orient=tk.VERTICAL, command=output.yview)
    output.configure(yscrollcommand=output_scroll.set)
    input = tk.Text(window, height=1, wrap='word')
    tabbar = ttk.Frame(window, height=16)

    # Grid widgets
    output.grid(column=0, row=0, sticky='nwes')
    output_scroll.grid(column=1, row=0, sticky='nwes')
    input.grid(column=0, row=1, columnspan=2, sticky='nwes')
    tabbar.grid(column=0, row=2, columnspan=2, sticky='nwes')

    # Configure for resizing
    window.columnconfigure(0, weight=1)
    window.rowconfigure(0, weight=1)

    # Final actions
    input.focus()

    return window, output, input, tabbar

def create_menus(window):
    window.option_add('*tearOff', False)
    menubar = tk.Menu(window)
    window['menu'] = menubar
    file = tk.Menu(menubar)
    menubar.add_cascade(menu=file, label='File')

def add_tab(client, player, puppet=''):
    tab = ttk.Frame(client.tabbar, padding=(5, 1), borderwidth=2, relief='raised')
    tab.player = player
    tab.puppet = puppet
    tab.grid(column=len(client.tabbar.grid_slaves()), row=0)
    if puppet:
        label = ttk.Label(tab, text=f'{puppet} - {player}')
    else:
        label = ttk.Label(tab, text=player)
    label.grid()

    tab.bind('<1>', lambda e: client.set_active_tab(tab))
    label.bind('<1>', lambda e: client.set_active_tab(tab))
