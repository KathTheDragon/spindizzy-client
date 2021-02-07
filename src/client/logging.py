from pathlib import Path
from datetime import datetime

def start(file):
    if file:
        with Path(file).open('a') as f:
            # f.write(header)
            pass

def log(file, *lines):
    if file:
        with Path(file).open('a') as f:
            for line in lines:
                # Add timestamp prefix
                f.write(line)

def stop(file):
    if file:
        with Path(file).open('a') as f:
            # f.write(footer)
            pass

