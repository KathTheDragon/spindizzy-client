import configparser, json
from pathlib import Path

configdir = Path().home() / '.sdclient'
configfile = configdir / 'config.cfg'
charfile = configdir / 'characters.json'
if not configdir.exists():
    configdir.mkdir()
if not charfile.exists():
    with charfile.open(mode='w') as f:
        f.write('{}')

class Config:
    def __init__(self):
        pass

def load_dict(dict, func):
    _dict = {}
    for key, value in dict.items():
        value = func(value)
        if value:
            _dict[key] = value
    return _dict

def load_player(player):
    if 'password' not in player:
        return {}
    else:
        return {
            'password': player['password'],
            'post-connect': player.get('post-connect', ''),
            'auto-connect': player.get('auto-connect', False),
            'log-file': player.get('log-file', ''),
            'puppets': load_dict(player.get('puppets', {}), load_puppet),
            # 'misc-tabs': load_dict(player.get('misc-tabs', {}), load_tab),
        }

def load_puppet(puppet):
    if 'action' not in puppet:
        return {}
    else:
        return {
            'action': puppet['action'],
            'auto-connect': puppet.get('auto-connect', False),
            'log-file': puppet.get('log-file', ''),
        }

# def load_tab(tab):
#     if 'send-prefix' not in tab or 'receive-prefix' not in tab:
#         return {}
#     else:
#         return {
#             'send-prefix': tab['send-prefix'],
#             'receive-prefix': tab['receive-prefix'],
#             'auto-connect': puppet.get('auto-connect', False),
#             'log-file': puppet.get('log-file', ''),
#         }

class Characters:
    def __init__(self):
        with charfile.open() as f:
            chars = json.load(f)
        self._chars = load_dict(chars, load_player)

    def __iter__(self):
        yield from self._chars

    def save(self):
        with charfile.open('w') as f:
            json.dump(self._chars, f)

    def add_player(self, player, password, postconnect=None, autoconnect=False, logfile=''):
        self._chars[player] = {
            'password': password,
            'post-connect': postconnect or [],
            'auto-connect': autoconnect,
            'log-file': logfile,
            'puppets': {},
            # 'misc-tabs': {}
        }

    def add_puppet(self, player, puppet, action, autoconnect=False, logfile=''):
        self._chars[player]['puppets'][puppet] = {
            'action': action,
            'auto-connect': autoconnect,
            'log-file': logfile
        }

    # def add_tab(self, player, tab, sendprefix, receiveprefix, autoconnect=False, logfile=''):
    #     self._chars[player]['misc-tabs'][puppet] = {
    #         'send-prefix': sendprefix,
    #         'receive-prefix': receiveprefix,
    #         'auto-connect': autoconnect,
    #         'log-file': logfile
    #     }

    def password(self, player):
        return self._chars.get(player, {}).get('password', '')

    def postconnect(self, player):
        return self._chars.get(player, {}).get('post-connect', [])

    def autoconnect(self, player, puppet=''):
        if puppet:
            return self._chars.get(player, {}).get('puppets', {}).get(puppet, {}).get('auto-connect', False)
        else:
            return self._chars.get(player, {}).get('auto-connect', False)

    def logfile(self, player, puppet=''):
        if puppet:
            return self._chars.get(player, {}).get('puppets', {}).get(puppet, {}).get('log-file', False)
        else:
            return self._chars.get(player, {}).get('log-file', False)

    def puppets(self, player):
        return self._chars.get(player, {}).get('puppets', {})
