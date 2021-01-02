from . import network, characters

class Client:
    def __init__(self):
        self.network = network.Network()
        self.characters = characters.CharacterList()
