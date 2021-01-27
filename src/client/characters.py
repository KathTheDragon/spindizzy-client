from dataclasses import dataclass, field
from typing import ClassVar

from .network import Connection

from .config import configdir
charfile = configdir / 'characters.json'
if not charfile.exists():
    with charfile.open(mode='w') as f:
        f.write('{}')

class InvalidCharacterData(Exception):
    pass

class MissingCharacterData(InvalidCharacterData):
    def __init__(self, cls, name, key):
        super().__init__(f'{cls.__name__} {name!r} missing key {key!r}')

class InvalidCharacter(Exception):
    def __init__(self, player, *, puppet='', tab='', reason=''):
        if puppet and tab:
            raise ValueError('cannot specify both puppet and tab')
        elif puppet:
            super().__init__(f'Puppet {puppet!r} of {player!r} {reason}')
        elif tab:
            super().__init__(f'Tab {tab!r} of {player!r} {reason}')
        else:
            super().__init__(f'Player {player!r} {reason}')

class CharacterAlreadyExists(InvalidCharacter):
    def __init__(self, player, *, puppet='', tab=''):
        super().__init__(player, puppet=puppet, tab=tab, reason='already exists')

class CharacterDoesNotExist(InvalidCharacter):
    def __init__(self, player, *, puppet='', tab=''):
        super().__init__(player, puppet=puppet, tab=tab, reason='does not exist')

def load(cls, characters):
    return {name: cls.load(name, data) for name, data in characters.items()}

def save(characters):
    return {name: character.save() for name, character in characters.items()}

@dataclass
class Character:
    name: str
    logfile: str
    buffer: list[str] = field(init=False, default_factory=list, repr=False, compare=False)

    @staticmethod
    def kwargs(data):
        return dict(
            logfile=data.get('log-file', '')
        )

    @classmethod
    def load(cls, name, data):
        for key in cls.__required__:
            if data.get(key, '') == '':
                raise MissingCharacterData(cls, name, key)
        return cls(name=name, **cls.kwargs(data))

    def save(self):
        return {
            'log-file': self.logfile
        }

    ## API
    def receive(self, message):
        self.buffer.append(message)
        if self.logfile:
            with open(self.logfile, mode='a') as f:
                # Overly simplistic
                f.write(message)
        return True

@dataclass
class Player(Character):
    __required__: ClassVar = ['password']
    password: str
    autoconnect: bool = False
    postconnect: list[str] = field(default_factory=list)
    tabs: dict[str, 'Tab'] = field(default_factory=dict)
    connection: Connection = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        self.connection = Connection(self.name, self.password)
        if self.autoconnect:
            self.connect()

    @staticmethod
    def kwargs(data):
        return super().kwargs(data) | dict(
            password=data.get('password'),
            autoconnect=data.get('auto-connect', False),
            postconnect=data.get('post-connect', []),
            tabs=(
                load(Puppet, data.get('puppets', {})) |
                load(Tab, data.get('misc-tabs', {}))
            ),
        )

    def save(self):
        puppets = {name: char for name, char in self.tabs.items() if isinstance(char, Puppet)}
        tabs = {name: char for name, char in self.tabs.items() if not isinstance(char, Puppet)}
        return super().save() | {
            'password': self.password,
            'auto-connect': self.autoconnect,
            'post-connect': self.postconnect,
            'puppets': save(puppets),
            'misc-tabs': save(tabs)
        }

    # API
    def connect(self):
        self.connection.open()
        # Connection preamble in buffer and log
        for line in self.postconnect:
            self.send(line)

    def disconnect(self):
        self.connection.close()
        # Disconnection postamble in buffer and log

    def send(self, message, puppet=''):
        if puppet:
            message = self[puppet].sendprefix + message
        self.connection.send(message)

    def receive(self):
        message = self.connection.receive()
        for tab in self.tabs:
            if tab.receive(message):
                return True
        else:
            return super().receive(message)

@dataclass
class Tab(Character):
    __required__ = ['send-prefix', 'receive-prefix']
    sendprefix: str
    receiveprefix: str
    removeprefix: bool = False

    @staticmethod
    def kwargs(data):
        return super().kwargs(data) | dict(
            sendprefix=data.get('send-prefix'),
            receiveprefix=data.get('receive-prefix'),
            removeprefix=data.get('remove-prefix', False),
        )

    def save(self):
        return super().save() | {
            'send-prefix': self.sendprefix,
            'receive-prefix': self.receiveprefix,
            'remove-prefix': self.removeprefix,
        }

    ## API
    def receive(self, message):
        if not message.startswith(self.receiveprefix):
            return False
        if self.removeprefix:
            message = message.removeprefix(self.receiveprefix)
        return super().receive(message)

@dataclass
class Puppet(Tab):
    __required__: ClassVar = ['action']
    action: str

    @staticmethod
    def kwargs(name, data):
        return super(Tab).kwargs(data) | dict(action=data.get('action'))

    def save(self):
        return super(Tab).save() | {'action': self.action}

    @property
    def sendprefix(self):
        return f'{self.action} '

    @property
    def receiveprefix(self):
        return f'{self.name}> '

    @property
    def removeprefix(self):
        return True

class CharacterList:
    def __init__(self):
        with charfile.open() as f:
            self.players = load(Player, json.load(f))

    def save(self):
        with charfile.open(mode='w') as f:
            json.dump(save(self.players), f)

    def characters(self):
        for name, player in self.players.items():
            yield name, ''
            for tab in player.tabs:
                yield name, tab

    def new_player(self, name, password, autoconnect=False, postconnect=(), logfile=''):
        if name in self.players:
            raise CharacterAlreadyExists(name)
        self.players[name] = Player(name, logfile, password, autoconnect, postconnect)
        self.save()

    def get_player(self, player):
        if player not in self.players:
            raise CharacterDoesNotExist(player)
        else:
            return self.players[player]

    def edit_player(self, player, name=None, password=None, autoconnect=None, postconnect=None, logfile=None):
        player = self.get_player(player)
        if name == '':
            raise ValueError
        if password == '':
            raise ValueError
        if name is not None and name not in self.players:
            self.players[name] = self.players.pop(player.name)
            player.name = name
        if password is not None:
            player.password = password
        if autoconnect is not None:
            player.autoconnect = autoconnect
        if postconnect is not None:
            player.postconnect = postconnect
        if logfile is not None:
            player.logfile = logfile

    def delete_player(self, player):
        self.get_player(player)
        del self.players[player]

    def new_puppet(self, player, name, action, logfile=''):
        player = self.get_player(player)
        if name in player.tabs:
            raise CharacterAlreadyExists(player, puppet=name)
        player.tabs[name] = Puppet(name, logfile, action)

    def get_puppet(self, player, puppet):
        player = self.get_player(player)
        if puppet not in player.tabs:
            raise CharacterDoesNotExist(player.name, puppet=puppet)
        puppet = player.tabs[puppet]
        if not isinstance(puppet, Puppet):
            raise CharacterDoesNotExist(player.name, puppet=puppet.name)
        else:
            return player, puppet

    def edit_puppet(self, player, puppet, name=None, action=None, logfile=None):
        player, puppet = self.get_puppet(player, puppet)
        if name == '':
            raise ValueError
        if action == '':
            raise ValueError
        if name is not None and name not in player.tabs:
            player.tabs[name] = player.tabs.pop(puppet.name)
            puppet.name = name
        if action is not None:
            puppet.action = action
        if autoconnect is not None:
            puppet.autoconnect = autoconnect
        if logfile is not None:
            puppet.logfile = logfile

    def delete_puppet(self, player, puppet):
        player, _ = self.get_puppet(player, puppet)
        del player.tabs[puppet]

    def new_tab(self, player, name, sendprefix, receiveprefix, logfile=''):
        player = self.get_player(player)
        if name in self.players[player].tabs:
            raise CharacterAlreadyExists(player, tab=name)
        player.tabs[name] = Tab(name, logfile, sendprefix, receiveprefix)

    def get_tab(self, player, tab):
        player = self.get_player(player)
        if tab not in player.tabs:
            raise CharacterDoesNotExist(player.name, tab=tab)
        tab = player.tabs[tab]
        if not isinstance(tab, Tab) or isinstance(tab, Puppet):
            raise CharacterDoesNotExist(player.name, tab=tab.name)
        else:
            return player, tab

    def edit_tab(self, player, tab, name=None, sendprefix=None, receiveprefix=None, logfile=None):
        player, tab = self.get_tab(player, tab)
        if name == '':
            raise ValueError
        if sendprefix == '':
            raise ValueError
        if receiveprefix == '':
            raise ValueError
        if name is not None and name not in player.tabs:
            player.tabs[name] = player.tabs.pop(tab.name)
            tab.name = name
        if sendprefix is not None:
            tab.sendprefix = sendprefix
        if receiveprefix is not None:
            tab.receiveprefix = receiveprefix
        if autoconnect is not None:
            tab.autoconnect = autoconnect
        if logfile is not None:
            tab.logfile = logfile

    def delete_tab(self, player, tab):
        player, _ = self.get_tab(player, tab)
        del player.tabs[tab]
