import json
from datetime import datetime

from . import logging
from .network import Connection

from .config import configdir
tabfile = configdir / 'tabs.json'
if not tabfile.exists():
    with tabfile.open(mode='w') as f:
        f.write('{}')

## Exceptions
class InvalidTabData(Exception):
    pass

class MissingTabData(InvalidTabData):
    def __init__(self, cls, name, key):
        super().__init__(f'{cls.__name__} {name!r} missing key {key!r}')

class InvalidTab(Exception):
    def __init__(self, *tabs, reason=''):
        super().__init__(f'{" - ".join(tabs)} {reason}')

class TabAlreadyExists(InvalidTab):
    def __init__(self, *tabs):
        super().__init__(*tabs, reason='already exists')

class TabDoesNotExist(InvalidTab):
    def __init__(self, *tabs):
        super().__init__(*tabs, reason='does not exist')

## Helper Functions
def load(cls, tabs, **kwargs):
    return {name: cls.load(name, data, **kwargs) for name, data in tabs.items()}

def save(tabs):
    return {name: tab.save() for name, tab in tabs.items()}

def gettype(type):
    if type == 'puppet':
        return Puppet
    elif type == 'tab':
        return Tab
    else:
        ValueError(f'invalid type {type!r}')

## Classes
__base_attrs__ = {
    'name': (None, None),
}

class Tab:
    __attrs__ = {
        'sendprefix': ('send-prefix', None),
        'receiveprefix': ('receive-prefix', None),
        'removeprefix': ('remove-prefix', False),
    }

    def __init__(self, name, parent=None, tabs=None, logger=None, **kwargs):
        attrs = {}
        clsname = self.__class__.__name__
        for attr, (key, default) in self.__attrs__.items():
            if default is None and attr not in kwargs:
                raise TypeError(f'{clsname}() missing required argument {attr!r}')
            elif default is None and kwargs.get(attr) == '':
                raise ValueError(f'{clsname}() missing required argument {attr!r}')
            else:
                attrs[attr] = kwargs.pop(attr, default)
        if kwargs:
            arg = next(iter(kwargs))
            raise TypeError(f'{clsname}() got an unexpected keyword argument {arg!r}')
        for attr, value in attrs.items():
            setattr(self, attr, value)
        self.name = name
        self.parent = parent
        self.tabs = load(Tab, tabs or {}, parent=self)
        self.logger = logging.Logger(**logger or {})
        self.buffer = []
        self.connected = False

    def __repr__(self):
        attrs = ['name', *self.__attrs__, 'parent', 'logger']
        arglist = [f'{attr}={getattr(self, attr)!r}' for attr in attrs]
        return f'{self.__class__.__name__}({", ".join(arglist)})'

    @classmethod
    def kwargs(cls, data, **attrs):
        attrs = cls.__attrs__ | {
            'logger': ('log', {}),
            'tabs': ('tabs', {}),
        } | attrs
        return {attr: data.get(k, d) for attr, (k, d) in cls.__attrs__.items()}

    @classmethod
    def load(cls, name, data, **kwargs):
        for key, default in cls.__attrs__.values():
            if default is None and data.get(key, '') == '':
                raise MissingTabData(cls, name, key)
        return cls(name=name, **cls.kwargs(data), **kwargs)

    def save(self):
        return {key: getattr(self, attr) for attr, (key, _) in self.__attrs__.items()} | {
            'log': self.logger._data(),
            'tabs': save(self.tabs),
        }

    ## Self Management
    def _edit(self, **kwargs):
        self.logger._edit(file=kwargs.pop('logfile', None), format=kwargs.pop('logformat', None))
        attrs = {}
        for attr, (key, default) in (__base_attrs__ | self.__attrs__).items():
            if default is None and kwargs.get(attr) == '':
                raise ValueError(f'{attr} cannot be blank')
            elif attr in kwargs:
                attrs[attr] = kwargs.pop(attr)
        if kwargs:
            raise TypeError(f'{next(iter(kwargs))} is not an editable attribute of {self.__class__.__name__!r}')
        for attr, value in attrs.items():
            setattr(self, attr, value)

    ## Tab Management
    def new(self, *, type='tab', name='', **kwargs):
        cls = gettype(type)
        if name == '':
            raise ValueError('name cannot be blank')
        elif name in self.tabs:
            raise TabAlreadyExists(self.name, name)
        else:
            self.tabs[name] = cls(name=name, **kwargs)
            return self.tabs[name]

    def get(self, tab):
        if tab not in self.tabs:
            raise TabDoesNotExist(self.name, tab)
        else:
            return self.tabs[tab]

    def edit(self, tab, **kwargs):
        self.get(tab)._edit(**kwargs)
        if 'name' in kwargs:
            name = kwargs['name']
            self.tabs[name] = self.tabs.pop(tab)

    def delete(self, tab):
        self.get(tab)
        del self.tabs[tab]

    def itertabs(self):
        for name, tab in self.tabs.items():
            yield (self.name, name)
            for names in tab.itertabs():
                yield (self.name, name, *names)

    ## API
    def connect(self, time):
        if not self.connected:
            if self.parent is not None:
                self.parent.connect(time)
            if self.logger.start(time):
                self.buffer.append(f'! Connected; logging to {self.logger.file!r}')
            else:
                self.buffer.append('! Connected')
            self.connected = True

    def disconnect(self, time):
        if self.connected:
            if self.logger.stop(time):
                self.buffer.append('! Disconnected; logging stopped')
            else:
                self.buffer.append('! Disconnected')
            self.connected = False
            for tab in self.tabs.values:
                tab.disconnect()

    def send(self, *messages):
        if messages:
            if not self.connected:
                self.connect(datetime.now())
            prefix = self.sendprefix
            messages = [prefix + message for message in messages]
            if self.parent is not None:
                self.parent.send(*messages)

    def receive(self, *messages):
        prefix = self.receiveprefix
        tabmessages = filter(lambda m: m.startswith(prefix), messages)
        if self.removeprefix:
            tabmessages = (message.removeprefix(prefix) for message in tabmessages)
        self._receive(*tabmessages)
        return filter(lambda m: not m.startswith(prefix), messages)

    def _receive(self, *messages):
        if messages:
            for tab in self.tabs.values():
                messages = tab.receive(*messages)
            if not self.connected:
                self.connect(messages[0].time)
            self.buffer.extend(messages)
            self.logger.log(*messages)

    def read(self, line=None, start=None, stop=None):
        self.update()
        if line is not None:
            if start is not None or stop is not None:
                raise TypeError('cannot specify line together with start or stop')
            else:
                return self.buffer[line]
        else:
            return self.buffer[slice(start, stop)]

    # Internal
    def update(self):
        if self.parent is not None:
            self.parent.update()

class Player(Tab):
    __attrs__ = {
        'password': ('password', None),
        'autoconnect': ('auto-connect', False),
        'postconnect': ('post-connect', ()),
    }

    def __init__(self, puppets=None, **kwargs):
        super().__init__(**kwargs)
        self.tabs |= load(Puppet, puppets or {}, parent=self)
        self.connection = Connection(self.name, self.password)
        if self.autoconnect:
            self.connect()

    @classmethod
    def kwargs(cls, data):
        return super().kwargs(data, puppets=('puppets', {}))

    def save(self):
        puppets = {name: char for name, char in self.tabs.items() if isinstance(char, Puppet)}
        tabs = {name: char for name, char in self.tabs.items() if not isinstance(char, Puppet)}
        return super().save() | {
            'puppets': save(puppets),
            'tabs': save(tabs)
        }

    # API
    def connect(self):
        self.connection.open()
        super().connect()
        for line in self.postconnect:
            self.send(line)

    def disconnect(self):
        if self.connection.isopen:
            self.connection.close()
        super().disconnect()

    def send(self, *messages):
        if messages:
            if not self.connected:
                self.connect(datetime.now())
            self.connection.send(*messages)

    def receive(self, *messages):
        self._receive(*messages)
        return ()

    # Internal
    def update(self):
        self.receive(*self.connection.receive())
        if not self.connection.isopen:
            self.disconnect()

class Puppet(Tab):
    __attrs__ = {
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

class TabList:
    def __init__(self):
        with tabfile.open() as f:
            self.players = load(Player, json.load(f))

    def save(self):
        with tabfile.open(mode='w') as f:
            json.dump(save(self.players), f)

    def characters(self):
        for name, player in self.players.items():
            yield (name,)
            yield from player.itertabs()

    # Player management
    def new_player(self, *, name='', **kwargs):
        if name == '':
            raise ValueError('name cannot be blank')
        elif name in self.players:
            raise TabAlreadyExists(name)
        else:
            self.players[name] = Player(name=name, **kwargs)
            return self.players[name]

    def get_player(self, player):
        if player not in self.players:
            raise TabDoesNotExist(player)
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

    # Tab Management
    def new(self, *parent, **kwargs):
        if not parent:
            char = self.new_player(**kwargs)
        else:
            char = self.get(*parent).new(**kwargs)
        self.save()
        return char

    def get(self, *tab):
        (*parent, tab) = tab
        if not parent:
            return self.get_player(tab)
        else:
            return self.get(*parent).get(tab)

    def edit(self, *tab, **kwargs):
        (*parent, tab) = tab
        if not parent:
            self.edit_player(tab, **kwargs)
        else:
            self.get(*parent).edit(tab, **kwargs)
        self.save()

    def delete(self, *tab):
        (*parent, tab) = tab
        if not parent:
            self.delete_player(tab)
        else:
            self.get(*parent).delete(tab)
        self.save()

    # Internal
    def update(self):
        for player in self.players.values():
            player.update()
