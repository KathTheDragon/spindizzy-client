import configparser, json
from pathlib import Path

configdir = Path().home() / '.sdclient'
configfile = configdir / 'config.cfg'
if not configdir.exists():
    configdir.mkdir()

class Config:
    def __init__(self):
        pass
