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

def gettype(type):
    if type == 'puppet':
        return Puppet
    elif type == 'tab':
        return Tab
    else:
        ValueError(f'invalid type {type!r}')

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

    ## Self Management
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

    # Puppet/Tab Management
    def new(self, type, *, name='', **kwargs):
        cls = gettype(type)
        if name == '':
            raise ValueError('name cannot be blank')
        elif name in self.tabs:
            raise CharacterAlreadyExists(self.name, **{type: name})
        else:
            self.tabs[name] = cls(name, **kwargs)
            return self.tabs[name]

    def get(self, type, tab):
        exc = CharacterDoesNotExist(player, **{type: tab})
        cls = gettype(type)
        if tab not in self.tabs:
            raise exc
        char = self.tabs[tab]
        if not isinstance(char, cls):
            raise exc
        return char

    def edit(self, type, tab, **kwargs):
        self.get(type, tab)._edit(**kwargs)
        if 'name' in kwargs:
            name = kwargs['name']
            self.tabs[name] = self.tabs.pop(tab)

    def delete(self, type, tab):
        self.get(type, tab)
        del self.tabs[tab]

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

    # Player management
    def new_player(self, *, name='', **kwargs):
        if name == '':
            raise ValueError('name cannot be blank')
        elif name in self.players:
            raise CharacterAlreadyExists(name)
        else:
            self.players[name] = Player(name, **kwargs)
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

    # Puppet management
    def new_puppet(self, player, **kwargs):
        puppet = self.get_player(player).new('puppet', **kwargs)
        self.save()
        return puppet

    def get_puppet(self, player, puppet):
        player = self.get_player(player)
        return player, player.get('puppet', puppet)

    def edit_puppet(self, player, puppet, **kwargs):
        self.get_player(player).edit('puppet', puppet, **kwargs)
        self.save()

    def delete_puppet(self, player, puppet):
        self.get_player(player).delete('puppet', puppet)
        self.save()

    # Non-puppet Tab management
    def new_tab(self, player, **kwargs):
        tab = self.get_player(player).new('tab', **kwargs)
        self.save()
        return tab

    def get_tab(self, player, tab):
        player = self.get_player(player)
        return player, player.get('tab', tab)

    def edit_tab(self, player, tab, **kwargs):
        self.get_player(player).edit('tab', tab, **kwargs)
        self.save()

    def delete_tab(self, player, tab):
        self.get_player(player).delete('tab', tab)
        self.save()
