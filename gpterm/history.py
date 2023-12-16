import dataclasses
import json
import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class HistoryEntry:
    content: str
    role: str = "user"

    @staticmethod
    def from_line(line: str):
        return HistoryEntry(**json.loads(line))


DEFAULT_HISTORY_FILE = os.getenv("CHAT_HISTORY_FILE", "./.chat_history")


@dataclass
class History:
    history: List[HistoryEntry]
    _start_index: int
    index: int
    file: str = DEFAULT_HISTORY_FILE

    def __init__(self, history: List[HistoryEntry], index: int, file: str = None):
        self.history = history
        self._start_index = len(history)
        self.index = index
        self.file = file or self.file

    @staticmethod
    def from_file(file: str = None):
        file = file or DEFAULT_HISTORY_FILE
        try:
            with open(file, "r") as f:
                history_lines = f.read().split("\n")
                history = [
                    HistoryEntry.from_line(line) for line in history_lines if line
                ]
                return History(history, len(history), file)
        except FileNotFoundError:
            return History([], 0, file)

    def save(self, file: str = None, append=True):
        file = file or self.file
        with open(file, "a" if append else "w") as file:
            file.write(
                "".join(
                    [
                        json.dumps(dataclasses.asdict(entry)) + "\n"
                        for entry in self.history[self._start_index :]
                    ]
                )
            )

    def __getitem__(self, index):
        return self.history[index]

    def __len__(self):
        return len(self.history)

    def append(self, entry: HistoryEntry):
        self.history.append(entry)
        self.index = len(self.history)

    def next(self):
        if self.index <= len(self.history):
            self.index += 1
        return self.current()

    def current(self):
        if 0 <= self.index < len(self.history):
            return self[self.index]

    def previous(self):
        if self.index >= 0:
            self.index -= 1
        return self.current()
