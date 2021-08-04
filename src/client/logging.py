from dataclasses import dataclass, asdict
from datetime import datetime
from itertools import starmap

@dataclass
class Logger:
    file: str = ''
    format: str = '{.time}  {.message}'

    def _data(self):
        return asdict(self)

    def _edit(self, file=None, format=None):
        if file is not None:
            self.file = file
        if format is not None:
            self.format = format

    def start(self, time):
        if self.file:
            with open(self.file, 'a') as f:
                print('*'*60, f'Logging Started: {time}', '-'*60, sep='\n', file=f)
            return True
        else:
            return False

    def log(self, *lines):
        if self.file:
            with open(self.file, 'a') as f:
                print(*starmap(self.format.format, lines), sep='\n', file=f)
            return True
        else:
            return False

    def stop(self, time):
        if self.file:
            with open(self.file, 'a') as f:
                print('-'*60, f'Logging Stopped: {time}', '*'*60, sep='\n', file=f)
            return True
        else:
            return False
