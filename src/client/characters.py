from dataclasses import dataclass, field
from typing import ClassVar

from .network import Connection
from .logging import LogFile

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
    logfile: LogFile
    buffer: list[str] = field(init=False, default_factory=list, repr=False, compare=False)
    connected: bool = field(init=False, default=False, repr=False, compare=False)

    @classmethod
    def kwargs(cls, data):
        return (
            dict(logfile=LogFile(data.get('log-file', ''))) |
            {attr: data.get(key, default) for attr, (key, default) in cls.__attrs__.items()}
        )

    @classmethod
    def load(cls, name, data):
        for key, default in cls.__attrs__.values():
            if default is None and data.get(key, '') == '':
                raise MissingCharacterData(cls, name, key)
        return cls(name=name, **cls.kwargs(data))

    def save(self):
        return (
            {'log-file': str(self.logfile.file or '')} |
            {key: getattr(self, attr) for attr, (key, default) in cls.__attrs__.items()}
        )

    def _edit(self, **kwargs):
        attrs = {}
        if 'logfile' in kwargs:
            attrs['logfile'] = LogFile(kwargs.pop('logfile'))
        for attr, (key, default) in ({'name': (None, None)} | self.__attrs__).items():
            if default is None and kwargs.get(attr) == '':
                raise ValueError(f'{attr} cannot be blank')
            elif attr in kwargs:
                attrs[attr] = kwargs.pop(attr)
        if kwargs:
            raise TypeError(f'{next(iter(kwargs))} is not an editable attribute of {self.__class__.__name__!r}')
        for attr, value in attrs.items():
            setattr(self, attr, value)

    ## API
    def receive(self, message):
        if not self.connected:
            self.connect()
        self.buffer.append(message)
        self.logfile.log(message)
        return True

    def connect(self):
        # Connection preamble
        self.logfile.start()

    def disconnect(self):
        # Disconnection postamble
        self.logfile.stop()

@dataclass
class Player(Character):
    __attrs__: ClassVar = {
        'password': ('password', None),
        'autoconnect': ('auto-connect', False),
        'postconnect': ('post-connect', ()),
    }
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
            tabs=(
                load(Puppet, data.get('puppets', {})) |
                load(Tab, data.get('misc-tabs', {}))
            ),
        )

    def save(self):
        puppets = {name: char for name, char in self.tabs.items() if isinstance(char, Puppet)}
        tabs = {name: char for name, char in self.tabs.items() if not isinstance(char, Puppet)}
        return super().save() | {
            'puppets': save(puppets),
            'misc-tabs': save(tabs)
        }

    # API
    def connect(self):
        self.connection.open()
        super().connect()
        for line in self.postconnect:
            self.send(line)

    def disconnect(self):
        self.connection.close()
        super().disconnect()
        for char in self.tabs.values():
            char.disconnect()

    def send(self, message, puppet=''):
        if puppet:
            message = self.tabs[puppet].sendprefix + message
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
    __attrs__: ClassVar = {
        'sendprefix': ('send-prefix', None),
        'receiveprefix': ('receive-prefix', None),
        'removeprefix': ('remove-prefix', False),
    }
    sendprefix: str
    receiveprefix: str
    removeprefix: bool = False

    ## API
    def receive(self, message):
        if not message.startswith(self.receiveprefix):
            return False
        if self.removeprefix:
            message = message.removeprefix(self.receiveprefix)
        return super().receive(message)

@dataclass
class Puppet(Tab):
    __attrs__: ClassVar = {
        'action': ('action', None),
    }
    action: str

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
        if name == '':
            raise ValueError('name cannot be blank')
        elif name in self.players:
            raise CharacterAlreadyExists(name)
        else:
            self.players[name] = Player(name, logfile, password, autoconnect, postconnect)
            self.save()
            return self.players[name]

    def get_player(self, player):
        if player not in self.players:
            raise CharacterDoesNotExist(player)
        else:
            return self.players[player]

    def edit_player(self, player, **kwargs):
        self.get_player(player)._edit(**kwargs)
        if 'name' in kwargs:
            name = kwargs['name']
            self.players[name] = self.players.pop(player)
        self.save()

    def delete_player(self, player):
        self.get_player(player)
        del self.players[player]
        self.save()

    def new_puppet(self, player, name, action, logfile=''):
        player = self.get_player(player)
        if name == '':
            raise ValueError('name cannot be blank')
        elif name in player.tabs:
            raise CharacterAlreadyExists(player.name, puppet=name)
        else:
            player.tabs[name] = Puppet(name, logfile, action)
            self.save()
            return player.tabs[name]

    def get_puppet(self, player, puppet):
        player = self.get_player(player)
        if puppet not in player.tabs:
            raise CharacterDoesNotExist(player.name, puppet=puppet)
        puppet = player.tabs[puppet]
        if not isinstance(puppet, Puppet):
            raise CharacterDoesNotExist(player.name, puppet=puppet.name)
        else:
            return player, puppet

    def edit_puppet(self, player, puppet, **kwargs):
        player, _puppet = self.get_puppet(player, puppet)
        _puppet._edit(**kwargs)
        if 'name' in kwargs:
            name = kwargs['name']
            player.tabs[name] = player.tabs.pop(puppet)
        self.save()

    def delete_puppet(self, player, puppet):
        player, _ = self.get_puppet(player, puppet)
        del player.tabs[puppet]
        self.save()

    def new_tab(self, player, name, sendprefix, receiveprefix, removeprefix=False, logfile=''):
        player = self.get_player(player)
        if name == '':
            raise ValueError('name cannot be blank')
        elif name in player.tabs:
            raise CharacterAlreadyExists(player.name, tab=name)
        else:
            player.tabs[name] = Tab(name, logfile, sendprefix, receiveprefix, removeprefix)
            self.save()
            return player.tabs[name]

    def get_tab(self, player, tab):
        player = self.get_player(player)
        if tab not in player.tabs:
            raise CharacterDoesNotExist(player.name, tab=tab)
        tab = player.tabs[tab]
        if not isinstance(tab, Tab) or isinstance(tab, Puppet):
            raise CharacterDoesNotExist(player.name, tab=tab.name)
        else:
            return player, tab

    def edit_tab(self, player, tab, **kwargs):
        player, _tab = self.get_tab(player, tab)
        _tab._edit(**kwargs)
        if 'name' in kwargs:
            name = kwargs['name']
            player.tabs[name] = player.tabs.pop(tab)
        self.save()

    def delete_tab(self, player, tab):
        player, _ = self.get_tab(player, tab)
        del player.tabs[tab]
        self.save()
