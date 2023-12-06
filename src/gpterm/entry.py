
import os
from typing import List

import atexit
from dotenv import load_dotenv
from readchar import readkey, key
from recordclass import dataobject
from dataclasses import dataclass
from time import sleep
import math

load_dotenv()

def pchar(char: str) -> None:
    """Print a character without a newline."""
    print(char, end="", flush=True)

class HistoryEntry(dataobject):
    user: str

@dataclass
class History:
    history: List[HistoryEntry]
    index: int

    def __getitem__(self, index):
        return self.history[index]

@dataclass
class Cursor:
    column: int
    row: int

@dataclass
class CursorMotion:
    column: int
    row: int

class Context:
    history: History
    _cursor: Cursor
    _lines: List[str]

    def __init__(self, history: History, lines: List[str]):
        self.history = history
        self._cursor = Cursor(0, 0)
        self._lines = lines.copy()

    def width(self):
        return os.get_terminal_size().columns

    @property
    def column(self):
        return self._cursor.column
    
    @column.setter
    def column(self, value):
        width = self.width()
        prev = self._cursor.column
        self._cursor.column = value
        if value > prev:
            print(key.RIGHT * (value - prev), end="", flush=True)
        else:
            print(key.LEFT * (prev - value), end="", flush=True)
        # print()
        # TODO: Handle lines
        # print("\r" + key.DOWN * ((value // width) - (prev // width)) + key.RIGHT * (value % width), end="")
    
    @property
    def row(self):
        return self._cursor.row
    
    @row.setter
    def row(self, value):
        prev = self.row
        value = max(value, 0)
        self._cursor.row = value
        if value > prev:
            print(key.DOWN * (value - prev), end="", flush=True)
        else:
            print(key.UP * (prev - value), end="", flush=True)

    @property
    def lines(self):
        return self._lines
    
    @lines.setter
    def lines(self, value: List[str]):
        value = value.copy()
        print("\r", end="")
        printed_lines = line_count(self.lines)
        queued_lines = line_count(value)
        extra_lines = printed_lines - queued_lines

        print(key.DOWN * (printed_lines - self.row), end="")

        width = self.width()
        clear = "\r" + " " * width
        print(key.UP.join([clear] * (extra_lines + 1)), end="\r")
        print(min(queued_lines, printed_lines) * key.UP, end="")
        for line in value:
            line = line.strip()
            empty = width - (len(line) % width)
            print(line + " " * empty)
        self._lines = [line for line in value]
        print(key.UP * (queued_lines - self.row), end="")
        print(key.RIGHT * self.column, end="", flush=True)

history_file = os.getenv("GPTERM_HISTORY_FILE", "./gpterm_history")
try:
    with open(history_file, "r") as file:
        history_lines = file.read().split("\n\n")
        history = History([HistoryEntry(line) for line in history_lines], len(history_lines))
except FileNotFoundError:
    history = []
    with open(history_file, "w") as file:
        file.write("")

# def handle_up() -> None:
#     """Handle the up arrow key."""
#     if history_index > 0:
#         history_index -= 1
#         fetched_lines = [x.strip() for x in history[history_index].split("\n") if x.strip()]
#         width = os.get_terminal_size().columns
#         print("\r", end="")
#         print((len(lines)) * key.UP, end="")
#         for line in fetched_lines:
#             print(line + " " * (width - len(line)))
#         lines = [line for line in fetched_lines]
def line_count(lines: List[str]) -> int:
    """Return the number of lines in the list."""
    width = os.get_terminal_size().columns
    return sum([math.ceil(len(line)/width) for line in lines])

def terminal_lines(lines: List[str]) -> int:
    """Return the lines as they would be printed to the terminal."""
    width = os.get_terminal_size().columns
    new_lines = []
    for line in lines:
        while len(line):
            new_lines.append(line[:width])
            line = line[width:]
    return new_lines

def write_char(char: str, context: Context) -> None:
    lines = [line for line in context.lines]
    line = lines[context.row]
    line = line[:context.column] + char + line[context.column:]
    lines[context.row] = line
    
    context.lines = lines
    context.column += 1

def remove_char(context: Context) -> None:
    lines = [line for line in context.lines]
    line = lines[context.row]
    line = line[:context.column - 1] + line[context.column:]
    lines[context.row] = line
    
    context.lines = lines
    context.column -= 1

def handle_key(char: str, context: Context) -> None:
    history = context.history
    if char == key.PAGE_UP:
        if history.index > 0:
            history.index -= 1
            context.lines = history[history.index].user.split("\n")
        else:
            history.index = max(0, history.index - 1)
            context.lines = [""]
        return True
    if char == key.PAGE_DOWN:
        if history.index < len(history.history) - 1:
            history.index += 1
            context.lines = history[history.index].user.split("\n")
        else:
            history.index = min(len(history.history) - 1, history.index + 1)
            context.lines = [""]
        return True
    if char == key.BACKSPACE:
        remove_char(context)
        return True
    if char == key.UP:
        context.row -= 1
        return True
    if char == key.DOWN:
        context.row += 1
        return True
    if char == key.LEFT:
        if context.column > 0:
            context.column -= 1
        return True
    if char == key.RIGHT:
        if context.column < len(context.lines[context.row]):
            context.column += 1
        return True

def get_input(prompt: str = "> ") -> str:
    entry = get_raw_input(prompt)
    entry = replace_files_with_contents(entry)
    return entry

def get_raw_input(prompt: str = "> ", history = history) -> str:
    print(prompt + "\n", end="", flush=True)
    context = Context(history, [])
    while True:
        line = ""
        while not line.endswith("\n"):
            char = readkey()
            if char == key.CTRL_D:
                print("\nGoodbye.")
                exit(0)
            if not handle_key(char, context):
                if len(char) > 1:
                    pchar(repr(char))
                    continue
                write_char(char, context)
        if not line.endswith(" "):
            data = "\n".join([line.strip() for line in context.lines])
            return data

def add_history_entry(entry: HistoryEntry, history: History = history) -> None:
    history.history.append(entry)

def replace_files_with_contents(message: str, directory: str = ".") -> str:
    """Replace filenames in the message with their contents."""
    for word in message.split():
        if word.startswith("<") and word.endswith(">"):
            filename = word[1:-1]
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                with open(filepath, "r") as file:
                    message = message.replace(word, file.read())
    return message