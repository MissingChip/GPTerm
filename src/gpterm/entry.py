
import os
import shutil
from typing import List

import atexit
from dotenv import load_dotenv
from readchar import readkey, key
from recordclass import dataobject
from dataclasses import dataclass
from time import time, sleep
import math

import logging
logger = logging.getLogger(__name__)


load_dotenv()

def praw(char: str, flush=True) -> None:
    """Print a character without a newline."""
    print(char, end="", flush=flush)

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
    row: int = 0
    column: int = 0

    def copy(self):
        return Cursor(self.row, self.column)

@dataclass
class CursorMotion:
    row: int = 0
    column: int = 0

class Context:
    history: History
    _cursor: Cursor
    _true_cursor: Cursor
    _lines: List[str]
    last_key: str = ""
    last_key_count: int = 0

    def __init__(self, history: History, lines: List[str]):
        self.history = history
        self._cursor = Cursor(0, 0)
        self._true_cursor = Cursor(0, 0)
        self._lines = lines.copy()

    def width(self):
        return os.get_terminal_size().columns

    @property
    def column(self):
        return self._cursor.column
    
    # @column.setter
    # def column(self, value):
    #     prev = self._cursor.column
    #     self._cursor.column = value
    #     if value > prev:
    #         print(key.RIGHT * (value - prev), end="", flush=True)
    #     else:
    #         print(key.LEFT * (prev - value), end="", flush=True)
        # print()
        # TODO: Handle lines
        # print("\r" + key.DOWN * ((value // width) - (prev // width)) + key.RIGHT * (value % width), end="")
    
    @property
    def row(self):
        return self._cursor.row
    
    # @row.setter
    # def row(self, value):
    #     prev = self.row
    #     value = min(max(value, 0), len(self.lines))
    #     self._cursor.row = value
    #     delta = value - prev
    #     if delta > 0:
    #         print(key.DOWN * (value - prev), end="", flush=True)
    #         if value == len(self.lines):
    #             print("\r", end="")
    #             self._true_cursor.column = 0
    #             self._lines.append("")
    #     elif delta < 0:
    #         print(key.UP * (prev - value), end="", flush=True)
    #     self._true_cursor.row += delta

    @property
    def lines(self):
        return self._lines
    
    @lines.setter
    def lines(self, value: List[str]):
        value = value.copy()
        self.clear()
        self.move_to_target(Cursor(0, 0))
        self._lines = value
        self.print_lines(value)
    
    def current_line(self):
        return self.lines[self.row]
    
    def move(self, motion: CursorMotion, flush=True):
        cursor = self._cursor.copy()
        cursor.row = min(max(self._cursor.row + motion.row, 0), len(self.lines) - 1)
        if cursor.column > len(self.lines[cursor.row]):
            cursor.column = len(self.lines[cursor.row])
        cursor.column += motion.column
        while cursor.column < 0:
            if cursor.row == 0:
                cursor.column = 0
                break
            cursor.row -= 1
            cursor.column += len(self.lines[cursor.row]) + 1
        while cursor.column > len(self.lines[cursor.row]):
            if cursor.row == len(self.lines) - 1:
                cursor.column = len(self.lines[cursor.row])
                break
            cursor.column -= len(self.lines[cursor.row])
            cursor.row += 1
        self._cursor = cursor
        self.move_to_target(flush=flush)

    def set_target(self, target: Cursor):
        self._cursor = target
    
    def move_to_target(self, target: Cursor = None, flush=True):
        if target is None:
            target = self._cursor
        width = self.width()
        target = Cursor(line_count(self.lines[:target.row]) + target.column // width, target.column % width)
        row_delta = target.row - self._true_cursor.row
        if row_delta > 0:
            praw(key.DOWN * row_delta, flush=flush)
        elif row_delta < 0:
            praw(key.UP * -row_delta, flush=flush)
        col_delta = target.column - self._true_cursor.column
        if col_delta > 0:
            praw(key.RIGHT * col_delta, flush=flush)
        elif col_delta < 0:
            praw(key.LEFT * -col_delta, flush=flush)
        self._true_cursor = target

    def _print_no_newlines(self, string: str, flush=False):
        width = self.width()
        praw(string, flush=flush)
        col = self._true_cursor.column + len(string)
        self._true_cursor.row += col // width
        self._true_cursor.column = col % width
    
    def _print_newline(self):
        praw("\n")
        self._cursor.row += 1
        self._cursor.column = 0
        self._true_cursor.row += 1
        self._true_cursor.column = 0

    def print_lines(self, lines: List[str]):
        for line in lines[:-1]:
            self._print_no_newlines(line)
            self._print_newline()
        self._print_no_newlines(lines[-1], flush=True)

    def print(self, string: str):
        lines = string.split("\n")
        self.print_lines(lines)

    def replace(self, string: str, start: int, end: int):
        assert "\n" not in string, "String cannot contain newlines."
        old_line = self.current_line()
        line_start = old_line[:start]
        line_end = old_line[end:]
        new_line = line_start + string + line_end
        spaces = max(len(old_line) - len(new_line), 0)
        self.move_to_target(Cursor(self.row, start))
        self.print(string + line_end + " " * spaces)
        self._lines[self.row] = new_line
        self.set_target(Cursor(self.row, start + len(string)))
        self.move_to_target()
        praw("", flush=True)

    def write(self, string: str):
        self.replace(string, self.column, self.column)
    
    def clear(self):
        width = self.width()
        self.move_to_target(Cursor(0, 0))
        count = line_count(self.lines)
        empty = " " * width
        print("\n".join([empty] * count), end="\r")
        self._true_cursor = Cursor(count, 0)

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

def terminal_width() -> int:
    return shutil.get_terminal_size().columns

def line_count(lines: List[str]) -> int:
    """Return the number of lines in the list."""
    width = terminal_width()
    return sum([math.ceil(len(line)/width) for line in lines])

def terminal_lines(lines: List[str]) -> int:
    """Return the lines as they would be printed to the terminal."""
    width = terminal_width()
    new_lines = []
    for line in lines:
        while len(line):
            new_lines.append(line[:width])
            line = line[width:]
    return new_lines

def write_char(char: str, context: Context) -> None:
    context.write(char)

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
            context.lines = history[history.index].user.split("\n") + [""]
        else:
            history.index = max(0, history.index - 1)
            context.lines = [""]
        return True
    if char == key.PAGE_DOWN:
        if history.index < len(history.history) - 1:
            history.index += 1
            context.lines = history[history.index].user.split("\n") + [""]
        else:
            history.index = min(len(history.history) - 1, history.index + 1)
            context.lines = [""]
        return True
    if char == key.BACKSPACE:
        remove_char(context)
        return True
    if char == key.UP:
        context.move(CursorMotion(-1))
        return True
    if char == key.DOWN:
        context.move(CursorMotion(1))
        return True
    if char == key.LEFT:
        context.move(CursorMotion(0, -1))
        return True
    if char == key.RIGHT:
        context.move(CursorMotion(0, 1))
        return True

def get_input(prompt: str = "> ") -> str:
    entry = get_raw_input(prompt)
    entry = replace_files_with_contents(entry)
    return entry

def get_raw_input(prompt: str = "> ", history = history) -> str:
    print(prompt + "\n", end="", flush=True)
    context = Context(history, [""])
    while True:
        while not context.lines[-1].endswith("\n"):
            char = readkey()
            if char == key.CTRL_D:
                print("\nGoodbye.")
                exit(0)
            times = 1
            if char == context.last_key:
                if time() - context.last_key_time < 0.25:
                    times = context.last_key_count + 1
            for _ in range(times):
                if not handle_key(char, context):
                    if len(char) > 1:
                        praw(repr(char))
                        continue
                    context.write(char)
            context.last_key = char
            context.last_key_count = times
            context.last_key_time = time()
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