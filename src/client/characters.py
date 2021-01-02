from dataclasses import dataclass, field
from typing import ClassVar

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

class CharacterAlreadyExists(Exception):
    def __init__(self, player, puppet=''):
        if puppet:
            super().__init__(f'Puppet {puppet!r} of {player!r} already exists')
        else:
            super().__init__(f'Player {player!r} already exists')

class CharacterDoesNotExist(Exception):
    def __init__(self, player, puppet=''):
        if puppet:
            super().__init__(f'Puppet {puppet!r} of {player!r} does not exist')
        else:
            super().__init__(f'Player {player!r} does not exist')

def loadchars():
    with charfile.open() as f:
        return load(Player, json.load(f))

def load(cls, characters):
    return {name: cls.load(name, data) for name, data in characters.items()}

def save(characters):
    return {name: character.save() for name, character in characters.items()}

@dataclass
class Character:
    name: str
    autoconnect: bool
    logfile: str

    @staticmethod
    def kwargs(data):
        return dict(
            autoconnect=data.get('auto-connect', False),
            logfile=data.get('log-file', '')
        )

    @classmethod
    def load(cls, name, data):
        for key in cls.__required__:
            if data.get(key, '') == '':
                raise MissingCharacterData(cls, name, key)
        return cls(name=name, **cls.kwargs(data))

@dataclass
class Player(Character):
    __required__: ClassVar = ['password']
    password: str
    postconnect: list[str]
    puppets: dict[str, 'Puppet']
    misctabs: dict[str, 'MiscTab']

    @staticmethod
    def kwargs(data):
        return super().kwargs(data) | dict(
            password=data.get('password'),
            postconnect=data.get('post-connect', []),
            puppets=load(Puppet, data.get('puppets', {})),
            misctabs=load(MiscTab, data.get('misc-tabs', {}))
        )

    def save(self):
        return super().save() | {
            'password': self.password,
            'post-connect': self.postconnect,
            'puppets': save(self.puppets),
            'misc-tabs': save(self.misctabs)
        }

    def __getitem__(self, puppet):
        if puppet in self.puppets:
            return self.puppets[puppet]
        elif puppet in self.misctabs:
            return self.misctabs[puppet]
        else:
            raise KeyError  # To-do: add an error message

    def __contains__(self, puppet):
        return puppet in self.puppets or puppet in self.misctabs

@dataclass
class Puppet(Character):
    __required__: ClassVar = ['action']
    action: str

    @staticmethod
    def load(name, data):
        return super().kwargs(data) | dict(
            action=data.get('action')
        )

    def save(self):
        return super().save() | {'action': self.action}

    @property
    def sendprefix(self):
        return f'{self.action} '

    @property
    def receiveprefix(self):
        return f'{self.name}> '

@dataclass
class MiscTab(Character):
    __required__ = ['send-prefix', 'receive-prefix']
    sendprefix: str
    receiveprefix: str

    @staticmethod
    def kwargs(data):
        return super().kwargs(data) | dict(
            sendprefix=data.get('send-prefix'),
            receiveprefix=data.get('receive-prefix')
        )

    def save(self):
        return super().save() | {
            'send-prefix': self.sendprefix,
            'receive-prefix': self.receiveprefix
        }

class CharacterList:
    def __init__(self):
        with charfile.open() as f:
            self.players = load(Player, json.load(f))

    def save(self):
        with charfile.open(mode='w') as f:
            json.dump(save(self.players), f)

    def __iter__(self):
        for name, player in self.players.items():
            yield name, ''
            for puppet in player.puppets:
                yield name, puppet
            for misctab in player.misctabs:
                yield name, misctab

    def __getitem__(self, character):
        if isinstance(character, str):
            return self.players[character]
        elif isinstance(character, tuple):
            player, puppet = character
            if puppet == '':
                return self.players[player]
            else:
                return self.players[player][puppet]
        else:
            raise TypeError  # To-do: Add an error message

    def __contains__(self, character):
        try:
            self[character]
        except KeyError:
            return False
        else:
            return True

    def new_player(self, name, password, postconnect=None, autoconnect=False, logfile=''):
        if name in self.players:
            raise CharacterAlreadyExists(name)
        self.players[name] = Player(name, autoconnect, logfile, password, postconnect, [], [])

    def edit_player(self, player, name=None, password=None, postconnect=None, autoconnect=None, logfile=None):
        if player not in self.players:
            raise CharacterDoesNotExist(player)
        if name == '':
            raise ValueError
        if password == '':
            raise ValueError
        player = self.players[player]
        if name is not None and name not in self.players:
            self.players[name] = self.players.pop(player.name)
            player.name = name
        if password is not None:
            player.password = password
        if postconnect is not None:
            player.postconnect = postconnect
        if autoconnect is not None:
            player.autoconnect = autoconnect
        if logfile is not None:
            player.logfile = logfile

    def delete_player(self, player):
        if player not in self.players:
            raise CharacterDoesNotExist(player)
        del self.players[player]

    def new_puppet(self, player, name, action, autoconnect=False, logfile=''):
        if player not in self.players:
            raise CharacterDoesNotExist(player)
        if name in self.players[player]:
            raise CharacterAlreadyExists(player, name)
        self.players[player].puppets[name] = Puppet(name, action, autoconnect, logfile)

    def edit_puppet(self, player, puppet, name=None, action=None, autoconnect=None, logfile=None):
        if player not in self.players:
            raise CharacterDoesNotExist(player)
        if puppet not in self.players[player]:
            raise CharacterDoesNotExist(player, puppet)
        if name == '':
            raise ValueError
        if action == '':
            raise ValueError
        puppet = self.players[player][puppet]
        if name is not None and name not in self.players[player]:
            self.players[player].puppets[name] = self.players[player].puppets.pop(puppet.name)
            puppet.name = name
        if action is not None:
            puppet.action = action
        if autoconnect is not None:
            puppet.autoconnect = autoconnect
        if logfile is not None:
            puppet.logfile = logfile

    def delete_puppet(self, player, puppet):
        if player not in self.players:
            raise CharacterDoesNotExist(player)
        if puppet not in self.players[player]:
            raise CharacterDoesNotExist(player, puppet)
        del self.players[player].puppets[puppet]

    def new_misctab(self, player, name, sendprefix, receiveprefix, autoconnect=False, logfile=''):
        if player not in self.players:
            raise CharacterDoesNotExist(player)
        if name in self.players[player]:
            raise CharacterAlreadyExists(player, name)
        self.players[player].misctabs[name] = MiscTab(name, sendprefix, receiveprefix, autoconnect, logfile)

    def edit_misctab(self, player, misctab, name='', sendprefix='', receiveprefix='', autoconnect=False, logfile=''):
        if player not in self.players:
            raise CharacterDoesNotExist(player)
        if misctab not in self.players[player]:
            raise CharacterDoesNotExist(player, misctab)
        if name == '':
            raise ValueError
        if sendprefix == '':
            raise ValueError
        if receiveprefix == '':
            raise ValueError
        misctab = self.players[player][misctab]
        if name is not None and name not in self.players[player]:
            self.players[player].misctabs[name] = self.players[player].misctabs.pop(misctab.name)
            misctab.name = name
        if sendprefix is not None:
            misctab.sendprefix = sendprefix
        if receiveprefix is not None:
            misctab.receiveprefix = receiveprefix
        if autoconnect is not None:
            misctab.autoconnect = autoconnect
        if logfile is not None:
            misctab.logfile = logfile

    def delete_misctab(self, player, misctab):
        if player not in self.players:
            raise CharacterDoesNotExist(player)
        if misctab not in self.players[player]:
            raise CharacterDoesNotExist(player, misctab)
        del self.players[player].misctabs[misctab]
