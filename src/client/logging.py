from pathlib import Path
from datetime import datetime

class LogFile:
    def __init__(self, file):
        if file:
            self.file = Path(file)
        else:
            self.file = None
        self.active = False

    def start(self):
        if self.file is None:
            return False
        else:
            self.active = True
            # .write() a header
            return True

    def log(self, line):
        if self.active or self.start():
            with self.file.open(mode='a') as f:
                # Add timestamp prefix
                f.write(line)

    def stop(self):
        if self.file is None:
            return False
        else:
            self.active = False
            # .write() a footer
            return True
