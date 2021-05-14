from pathlib import Path
from datetime import datetime

def start(file, time):
    if file:
        with Path(file).open('a') as f:
            f.write(f'{"":*<60}\nLogging Started: {time}\n{"":-<60}\n')

def log(file, *lines):
    if file:
        with Path(file).open('a') as f:
            for time, line in lines:
                f.write(str(line))

def stop(file, time):
    if file:
        with Path(file).open('a') as f:
            f.write(f'{"":-<60}\nLogging Stopped: {time}\n{"":*<60}\n')

