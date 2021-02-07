import json
from dataclasses import dataclass, field
from typing import ClassVar

from . import logging
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

def load(cls, characters, **kwargs):
    return {name: cls.load(name, data, **kwargs) for name, data in characters.items()}

def save(characters):
    return {name: character.save() for name, character in characters.items()}

def gettype(type):
    if type == 'puppet':
        return Puppet
    elif type == 'tab':
        return Tab
    else:
        ValueError(f'invalid type {type!r}')

class Character:
    def __init__(self, **kwargs):
        attrs = {}
        for attr, (key, default) in ({'name': (None, None)} | self.__attrs__).items():
            if default is None and attr not in kwargs:
                raise TypeError(f'{self.__class__.__name__}() missing required argument {attr!r}')
            elif default is None and kwargs.get(attr) == '':
                raise ValueError(f'{self.__class__.__name__}() missing required argument {attr!r}')
            else:
                attrs[attr] = kwargs.pop(attr, default)
        attrs['logfile'] = kwargs.pop('logfile', '')
        if kwargs:
            raise TypeError(f'{self.__class__.__name__}() got an unexpected keyword argument {next(iter(kwargs))!r}')
        for attr, value in attrs.items():
            setattr(self, attr, value)
        self.buffer = []
        self.connected = False

    def __repr__(self):
        arglist = []
        for attr in ['name'] + list(self.__attrs__):
            arglist.append(f'{attr}={getattr(self, attr)!r}')
        arglist.append(f'logfile={self.logfile!r}')
        return f'{self.__class__.__name__}({", ".join(arglist)})'

    @classmethod
    def kwargs(cls, data):
        return (
            dict(logfile=data.get('log-file', '')) |
            {attr: data.get(key, default) for attr, (key, default) in cls.__attrs__.items()}
        )

    @classmethod
    def load(cls, name, data, **kwargs):
        for key, default in cls.__attrs__.values():
            if default is None and data.get(key, '') == '':
                raise MissingCharacterData(cls, name, key)
        return cls(name=name, **cls.kwargs(data), **kwargs)

    def save(self):
        return (
            {'log-file': self.logfile} |
            {key: getattr(self, attr) for attr, (key, default) in self.__attrs__.items()}
        )

    ## Self Management
    def _edit(self, **kwargs):
        attrs = {}
        if 'logfile' in kwargs:
            attrs['logfile'] = kwargs.pop('logfile')
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
    def receive(self, *messages):
        if not self.connected:
            self.connect()
        self.buffer.extend(messages)
        logging.log(self.logfile, *messages)
        return ()

    def connect(self):
        # Connection preamble
        logging.start(self.logfile)
        self.connected = True

    def disconnect(self):
        # Disconnection postamble
        logging.stop(self.logfile)
        self.connected = False

    def read(self, line=None, start=None, stop=None):
        self.update()
        if line is not None:
            if start is not None or stop is not None:
                raise TypeError('cannot specify line together with start or stop')
            else:
                return self.buffer[line]
        else:
            return self.buffer[slice(start, stop)]

class Player(Character):
    __attrs__: ClassVar = {
        'password': ('password', None),
        'autoconnect': ('auto-connect', False),
        'postconnect': ('post-connect', ()),
    }

    def __init__(self, **kwargs):
        tabs = kwargs.pop('tabs', {})
        super().__init__(**kwargs)
        self.tabs = {}
        for name, tab in tabs.items():
            tab.player = self
            self.tabs[name] = tab
        self.connection = Connection(self.name, self.password)
        if self.autoconnect:
            self.connect()

    @classmethod
    def kwargs(cls, data):
        return super().kwargs(data) | dict(
            tabs=(
                load(Puppet, data.get('puppets', {})) |
                load(Tab, data.get('misc-tabs', {}))
            ),
        )

    @classmethod
    def load(cls, name, data):
        puppets = data.get('puppets', {})
        misctabs = data.get('misctabs', {})
        player = super().load(name, data)
        player.tabs = (
            load(Puppet, puppets, player=player) |
            load(Tab, misctabs, player=player)
        )
        return player

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
            self.tabs[name] = cls(name=name, **kwargs)
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

    def send(self, *messages):
        self.connection.send(*messages)

    def receive(self, *messages):
        for tab in self.tabs.values():
            messages = tab.receive(*messages)
        return super().receive(*messages)

    # Internal
    def update(self):
        self.receive(*self.connection.receive())

class Tab(Character):
    __attrs__: ClassVar = {
        'sendprefix': ('send-prefix', None),
        'receiveprefix': ('receive-prefix', None),
        'removeprefix': ('remove-prefix', False),
    }

    def __init__(self, **kwargs):
        self.player = kwargs.pop('player', None)
        super().__init__(**kwargs)

    ## API
    def send(self, *messages):
        prefix = self.sendprefix
        messages = [prefix + message for message in messages]
        self.player.send(*messages)

    def receive(self, *messages):
        prefix = self.receiveprefix
        childmessages = filter(lambda m: m.startswith(prefix), messages)
        if self.removeprefix:
            childmessages = (message.removeprefix(prefix) for message in childmessages)
        super().receive(*childmessages)
        return filter(lambda m: not m.startswith(prefix), messages)

    # Internal
    def update(self):
        self.player.update()

class Puppet(Tab):
    __attrs__: ClassVar = {
        'action': ('action', None),
    }

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
            self.players[name] = Player(name=name, **kwargs)
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

    def delete_player(self, player):
        self.get_player(player)
        del self.players[player]

    # Character Management
    def new(self, type, player='', **kwargs):
        if type == 'player':
            char = self.new_player(**kwargs)
        else:
            char = self.get_player(player).new(type, **kwargs)
        self.save()
        return char

    def get(self, type, player, char=''):
        if type == 'player':
            return self.get_player(player)
        else:
            return self.get_player(player).get(type, char)

    def edit(self, type, player, char='', **kwargs):
        if type == 'player':
            self.edit_player(player, **kwargs)
        else:
            self.get_player(player).edit(type, char, **kwargs)
        self.save()

    def delete(self, type, player, char=''):
        if type == 'player':
            self.delete_player(player)
        else:
            self.get_player(player).delete(type, char)
        self.save()

    # Internal
    def update(self):
        for player in self.players.values():
            player.update()
