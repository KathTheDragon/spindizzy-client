from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
from itertools import starmap

@dataclass
class Logger:
    file: Path
    format: str

    def _data(self):
        return asdict(self)

    def _edit(self, file=None, format=None):
        if file is not None:
            self.file = Path(file)
        if format is not None:
            self.format = format

    def start(self, time):
        with self.file.open('a') as f:
            print('*'*60, f'Logging Started: {time}', '-'*60, sep='\n', file=f)

    def log(self, *lines):
        with self.file.open('a') as f:
            print(*starmap(self.format.format, lines), sep='\n', file=f)

    def stop(self, time):
        with self.file.open('a') as f:
            print('-'*60, f'Logging Stopped: {time}', '*'*60, sep='\n', file=f)
