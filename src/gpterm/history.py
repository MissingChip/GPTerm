
from dotenv import load_dotenv
import dataclasses
from dataclasses import dataclass
import os
import sys
import shutil
from typing import List

import atexit
from readchar import readkey, key
from recordclass import dataobject
from time import time, sleep
import math
import json

load_dotenv()

@dataclass
class HistoryEntry:
    content: str
    role: str = "user"

    @staticmethod
    def from_line(line: str):
        return HistoryEntry(**json.loads(line))

DEFAULT_HISTORY_FILE = os.getenv("GPTERM_HISTORY_FILE", "./gpterm_history")
@dataclass
class History:
    history: List[HistoryEntry]
    index: int
    file: str = DEFAULT_HISTORY_FILE

    def __init__(self, history: List[HistoryEntry], index: int, file: str = None):
        self.history = history
        self.index = index
        self.file = file or self.file
    
    @staticmethod
    def from_file(file: str = None):
        file = file or DEFAULT_HISTORY_FILE
        try:
            with open(file, "r") as f:
                history_lines = f.read().split("\n")
                history = [HistoryEntry.from_line(line) for line in history_lines if line]
                return History(history, len(history), file)
        except FileNotFoundError:
            return History([], 0, file)
    
    def save(self, file: str = None, append=True):
        file = file or self.file
        with open(file, "a" if append else "w") as file:
            file.write("\n".join([json.dumps(dataclasses.asdict(entry)) for entry in self.history]))

    def __getitem__(self, index):
        return self.history[index]
    
    def __len__(self):
        return len(self.history)
    
    def append(self, entry: HistoryEntry):
        self.history.append(entry)
        self.index = len(self.history)