from . import ui

class Client:
    def __init__(self):
        self.window, self.output, self.input, self.tabbar = ui.create()
        self.set_title()

    def set_title(self, player='', puppet=''):
        if not player:
            self.root.title('Spindizzy')
        elif not puppet:
            self.root.title(f'{player} - Spindizzy')
        else:
            self.root.title(f'{puppet} - {player} - Spindizzy')
