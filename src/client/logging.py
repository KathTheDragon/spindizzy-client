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
        if self.file is None or self.active:
            return False
        else:
            self.active = True
            # .write() a header
            return True

    def log(self, *lines):
        if self.active:
            with self.file.open(mode='a') as f:
                for line in lines:
                    # Add timestamp prefix
                    f.write(line)
            return True
        else:
            return False

    def stop(self):
        if self.file is None or not self.active:
            return False
        else:
            self.active = False
            # .write() a footer
            return True
