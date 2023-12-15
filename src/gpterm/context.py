
from dataclasses import dataclass
import os
import sys
import shutil
from typing import List

import atexit
from gpterm.chario import readkey, key, init_chario
from recordclass import dataobject
from time import time, sleep
import math
import json

import logging

from gpterm.history import History, HistoryEntry
logger = logging.getLogger(__name__)
# TODO not at the top level
init_chario()

def praw(string: str, flush=True) -> None:
    """Print a character without a newline."""
    sys.stdout.write(string)
    if flush:
        sys.stdout.flush()

def hide_cursor() -> None:
    """Hide the cursor."""
    praw("\033[?25l")

def show_cursor() -> None:
    """Show the cursor."""
    praw("\033[?25h")

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
    _target_cursor: Cursor
    _term_cursor: Cursor
    _term_lines: List[str]
    last_key: str = ""
    last_key_count: int = 0

    def __init__(self, history: History = None, lines: List[str] = []):
        self.history = history or History.from_file()
        self._target_cursor = Cursor(0, 0)
        self._term_cursor = Cursor(0, 0)
        self._term_lines = []
        self.set(lines)

    def width(self):
        return terminal_width()

    @property
    def column(self):
        return self._target_cursor.column
    
    @property
    def row(self):
        return self._target_cursor.row
    
    @property
    def value(self):
        return "".join(self._value).rstrip("\n")
    
    def set(self, value: str | List[str]):
        self._value = terminal_lines(value, self.width())
        # logger.debug(f"Set value: {self._value}")
        self.draw()
        self.jump_to_end()
        show_cursor()
        logger.debug(f"Set value, cursor at {self._target_cursor}: {self._value}")
    
    def term_line(self, lineno: int):
        return self._term_lines[lineno].rstrip("\n")
    
    def move(self, motion: CursorMotion, flush=True):
        row = self._target_cursor.row
        col = self._target_cursor.column
        row = row + motion.row
        if row < 0:
            logger.debug(f"Moving cursor {motion} from {self._target_cursor} to {row}, {col}")
            self._value = (["\n"] * -row) + self._value
            self.draw()
            self.set_target(Cursor())
            return
        lines = self._term_lines
        if row >= len(lines):
            self._value[-1] += "\n"
            self.set(self._value + (["\n"] * (row - len(lines))) + [""])
            return
        logger.debug(f"Moving cursor {motion} from {self._target_cursor} to {row}, {col}")
        sz = lambda row: len(lines[row].rstrip("\n"))
        if col > sz(row):
            col = sz(row)
        col += motion.column
        while col < 0:
            if row == 0:
                col = 0
                break
            row -= 1
            col += sz(row) + 1
        while col > sz(row):
            if row == len(lines) - 1:
                col = sz(row)
                break
            col -= sz(row) + 1
            row += 1
        self._target_cursor = Cursor(row, col)
        self.move_to_target(flush=flush)

    def set_target(self, target: Cursor, move=True):
        self._target_cursor = target
        if move:
            self.move_to_target()
    
    def jump_to_end(self):
        self.set_target(Cursor(len(self._term_lines)-1, len(self._term_lines[-1])))
    
    def _cursor_visualization(self, cursor: Cursor = None):
        if cursor is None:
            cursor = self._target_cursor
        row = cursor.row
        col = cursor.column
        return repr(f"{self._value[row][:col]}|{self._value[row][col:]}")
    
    def move_to_target(self, target: Cursor = None, flush=True):
        if target is None:
            target = self._target_cursor
        logger.debug(f"Target: cursor {target} ({self._term_cursor})")
        width = self.width()
        target = Cursor(target.row + target.column // width, target.column % width)
        row_delta = target.row - self._term_cursor.row
        self._term_cursor = target
        val = ""
        if row_delta > 0:
            val += "\n" * row_delta
        elif row_delta < 0:
            val += key.UP * -row_delta
        val += "\r" + key.RIGHT * target.column
        praw(val, flush=flush)
    
    def backspace(self):
        cursor = self._target_cursor
        if cursor.column > 0:
            self.replace("", Cursor(cursor.row, cursor.column-1), cursor)
        elif cursor.row > 0:
            self.replace("", Cursor(cursor.row-1, -1), cursor)
    
    def tab(self):
        current_column = self._target_cursor.column
        spaces = 4 - (current_column % 4)
        self.write(" " * spaces)
    
    def backtab(self):
        line = self._term_lines[self._target_cursor.row].rstrip("\n")
        row = self._target_cursor.row
        end_column = len(line) - len(line.lstrip(" "))
        start_column = end_column - ((end_column % 4) or 4)
        self.replace("", Cursor(row, start_column), Cursor(row, end_column))

    def replace(self, string: str, start: Cursor, end: Cursor):
        # logger.debug(f"Replacing {start} to {end} with {repr(string)}, {self._value}")
        # logger.debug(f"Before: {self._cursor_visualization()}")
        lines = string.split("\n")
        line_start = self._value[start.row][:start.column]
        line_end = self._value[end.row][end.column:]

        # TODO: Have terminal_lines() handle this?
        lines[0] = line_start + lines[0]
        lines[-1] += line_end
        lines = [line + "\n" for line in lines[:-1]] + [lines[-1]]
        logger.debug(f"Replacing {start} to {end} with {lines}")

        self._value = self._value[:start.row] + lines + self._value[end.row+1:]

        self._value = self.draw().copy()
        self.set_target(Cursor(start.row + len(lines) - 1, len(lines[-1])))
        self.move_to_target()
        show_cursor()

    def write(self, string: str):
        self.replace(string, self._target_cursor, self._target_cursor)

    def _mismatch_index(self, term_lines: List[str]):
        for i, (line, term_line) in enumerate(zip(self._term_lines, term_lines)):
            if line != term_line:
                return i
        return min(len(self._term_lines), len(term_lines))
    
    def draw(self, lines: str | List[str] = None):
        if lines is None:
            lines = self._value
        width = self.width()
        hidden = False
        term = terminal_lines(lines, width)
        mismatch = self._mismatch_index(term)
        limit = max(len(term), len(self._term_lines))
        for lineno in range(mismatch, limit):
            line = term[lineno] if lineno < len(term) else ""
            line = line.rstrip()
            original = self._term_lines[lineno] if lineno < len(self._term_lines) else None
            original = original and original.rstrip()
            if line != original:
                original = original or ""
                if len(line) - 1 == len(original or ""):
                    praw(line[-1])
                    self._term_cursor.column += 1
                else:
                    if not hidden:
                        hide_cursor()
                        hidden = True
                    self.move_to_target(Cursor(lineno))
                    spaces = max(len(original) - len(line), 0) * " "
                    praw("\r" + line + spaces + "\r")
                    # logger.debug(f"Drawing {repr(line)}")
        self._term_lines = term
        return self._term_lines

    def _return(self):
        self.jump_to_end()
        praw("\n")
        value = self.value
        self.history.append(HistoryEntry(value))
        self._value = [""]
        return value

    def next(self, prompt=""):
        """Get the next block of input from the user"""
        if prompt:
            print(prompt)
        while True:
            char = readkey()
            logger.debug(f"Read key: {repr(char)}")
            if char == key.CTRL_D:
                self.jump_to_end()
                print("\n")
                return None
            if len(self._value) == 1 and char == key.ENTER:
                return self._return()
            if char == "\r":
                continue
            times = 1
            if char == self.last_key and time() - self.last_key_time < 0.25:
                if char == key.ENTER:
                    return self._return()
                self.last_key_count += 1
                times = repeat_times(self.last_key_count)
            else:
                self.last_key_count = 0
            if not handle_key(char, self, times):
                if len(char) > 1:
                    logger.debug(f"Skipping long character: {repr(char)} {char}")
                    continue
                self.write(char * times)
            self.last_key = char
            self.last_key_time = time()
    def save(self):
        self.history.save()

def repeat_times(times_repeated: int):
    return 1 if times_repeated <= 2 else min(times_repeated + 2, 12)

def terminal_width() -> int:
    return shutil.get_terminal_size().columns

def line_count(lines: List[str]) -> int:
    """Return the number of lines in the list."""
    width = terminal_width()
    return sum([math.ceil(len(line)/width) for line in lines])

def flatten(xss):
    return [x for xs in xss for x in xs]

def terminal_lines(lines: str | List[str], width=terminal_width()) -> int:
    """Return the lines as they would be printed to the terminal."""
    if isinstance(lines, str):
        lines = lines.splitlines(True)
    # else:
    #     lines = flatten([line.splitlines(True) for line in lines])
    new_lines = []
    for line in lines:
        end = ""
        if line.endswith("\n"):
            end = "\n"
            line = line.rstrip("\n")
        while len(line) > width:
            new_lines.append(line[:width])
            line = line[width:]
        new_lines.append(line + end)
    return new_lines or [""]

def handle_key(char: str, context: Context, count: int) -> None:
    history = context.history
    logger.debug(f"Handling key: {repr(char)}")
    if char in (key.PAGE_UP, key.SHIFT_UP):
        value = history.previous()
        context.set((value and value.content) or "")
        return True
    if char in (key.PAGE_DOWN, key.SHIFT_DOWN):
        value = history.next()
        context.set((value and value.content) or "")
        return True
    if char == key.TAB:
        context.tab()
        return True
    if char == key.SHIFT_TAB:
        context.backtab()
        return True
    if char == key.BACKSPACE:
        for _ in range(count):
            context.backspace()
        return True
    if char == key.UP:
        context.move(CursorMotion(-min(count, 4)))
        return True
    if char in (key.DOWN, key.ALT_ENTER):
        context.move(CursorMotion(min(count, 4)))
        return True
    if char == key.LEFT:
        context.move(CursorMotion(0, -count))
        return True
    if char == key.RIGHT:
        context.move(CursorMotion(0, count))
        return True

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