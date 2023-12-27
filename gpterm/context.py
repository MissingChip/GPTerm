import logging
import math
import os
import shutil
import sys
from dataclasses import dataclass
from time import sleep, time
from typing import List, Union

from gpterm.chario import init_chario, key, readkey
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
    last_key_time: float = 0
    line_start = ""

    def __init__(
        self, history: History = None, lines: List[str] = [], line_start: str = ""
    ):
        self.history = history or History.from_file()
        self.line_start = line_start
        self.reset(False)

    def reset(self, val=True):
        self._target_cursor = Cursor(0, 0)
        self._term_cursor = Cursor(0, 0)
        self._term_lines = []
        self.last_key_time = time()
        self.last_key = ""
        self.last_key_count = 0
        if val:
            self.set([""])

    def width(self):
        return terminal_width() - len(self.line_start)

    @property
    def column(self):
        return self._target_cursor.column

    @property
    def row(self):
        return self._target_cursor.row

    @property
    def value(self):
        return "".join(self._value).rstrip("\n")

    def set(self, value: Union[str,List[str]]):
        self._value = terminal_lines(value, self.width())
        self.draw()
        self.jump_to_end()
        show_cursor()

    def term_line(self, lineno: int):
        return self._term_lines[lineno].rstrip("\n")

    def move(self, motion: CursorMotion, flush=True):
        row = self._target_cursor.row
        col = self._target_cursor.column
        row = row + motion.row
        if row < 0:
            self._value = (["\n"] * -row) + self._value
            self.draw()
            self.set_target(Cursor())
            return
        lines = self._term_lines
        if row >= len(lines):
            self._value[-1] += "\n"
            self.set(self._value + (["\n"] * (row - len(lines))) + [""])
            return
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
        self.set_target(Cursor(len(self._term_lines) - 1, len(self._term_lines[-1])))

    def _cursor_visualization(self, cursor: Cursor = None):
        if cursor is None:
            cursor = self._target_cursor
        row = cursor.row
        col = cursor.column
        if row >= len(self._value):
            return repr(f"{self._value[-1]}|")
        return repr(f"{self._value[row][:col]}|{self._value[row][col:]}")

    def move_to_target(self, target: Cursor = None, flush=True):
        if target is None:
            target = self._target_cursor
        width = self.width()
        target = Cursor(target.row + target.column // width, target.column % width)
        self._target_cursor = target
        logger.debug(f"Moving to {target}")
        row_delta = target.row - self._term_cursor.row
        self._term_cursor = target
        val = ""
        if row_delta > 0:
            val += "\n" * row_delta
        elif row_delta < 0:
            val += key.UP * -row_delta
        val += "\r" + key.RIGHT * (target.column + len(self.line_start))
        praw(val, flush=flush)
        # if target.row >= len(self._value):
        #     self._value[-1] += "\n"
        #     self._value += [""]
        #     return

    def backspace(self, amount=1):
        cursor = self._target_cursor
        if cursor.column >= amount:
            self.replace("", Cursor(cursor.row, cursor.column - amount), cursor)
        elif cursor.row > 0:
            line = len(self._value[cursor.row - 1])
            self.replace("", Cursor(cursor.row - 1, line-amount), cursor)
        else:
            self.replace("", Cursor(0, 0), cursor)

    def delete(self):
        cursor = self._target_cursor
        if cursor.column < len(self._value[cursor.row]):
            self.replace("", cursor, Cursor(cursor.row, cursor.column + 1))
        elif cursor.row < len(self._value) - 1:
            self.replace("", cursor, Cursor(cursor.row + 1, 0))

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
        logger.debug(f"Replacing {string} {start} {end}")
        lines = string.split("\n")
        line_start = self._value[start.row][: start.column]
        line_end = self._value[end.row][end.column :]

        # TODO: Have terminal_lines() handle this?
        lines[0] = line_start + lines[0]
        end_len = len(lines[-1])
        lines[-1] += line_end
        lines = [line + "\n" for line in lines[:-1]] + [lines[-1]]

        self._value = self._value[: start.row] + lines + self._value[end.row + 1 :]

        self._value = self.draw(self._value).copy()
        self.set_target(Cursor(start.row + len(lines) - 1, end_len))
        logger.debug(f"Cursor: {self.width()} {end_len} {self._cursor_visualization()}")
        show_cursor()

    def write(self, string: str):
        self.replace(string, self._target_cursor, self._target_cursor)

    def _mismatch_index(self, term_lines: List[str]):
        for i, (line, term_line) in enumerate(zip(self._term_lines, term_lines)):
            if line != term_line:
                return i
        return min(len(self._term_lines), len(term_lines))

    def draw(self, lines: List[str] = None):
        if lines is None:
            lines = self._value
        width = self.width()
        hidden = False
        term = terminal_lines(lines, width)
        logger.debug(f"Drawing {term} on {self._term_lines}")
        mismatch = self._mismatch_index(term)
        limit = max(len(term), len(self._term_lines))
        for lineno in range(mismatch, limit):
            line = term[lineno] if lineno < len(term) else ""
            line = line.rstrip()
            original = (
                self._term_lines[lineno] if lineno < len(self._term_lines) else None
            )
            original = original and original.rstrip()
            if lineno >= len(term):
                self.move_to_target(Cursor(lineno))
                praw("\r" + " " * width + "\r")
            elif line != original:
                original = original or ""
                col = self._term_cursor.column
                if original and line[:col] == original:
                    praw(line[col:])
                    self._term_cursor.column += 1
                else:
                    if not hidden:
                        hide_cursor()
                        hidden = True
                    self.move_to_target(Cursor(lineno))
                    spaces = max(len(original) - len(line), 0) * " "
                    praw("\r" + self.line_start + line + spaces + "\r")
        self._term_lines = term
        logger.debug("Done drawing")
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
        self.reset()
        while True:
            char = readkey()
            if char == key.CTRL_D:
                self.jump_to_end()
                print("\n")
                return None
            if len(self._value) == 1 and char == key.ENTER:
                return self._return()
            if char == "\r":
                continue
            times = 1
            deltat = time() - self.last_key_time
            if char == self.last_key and deltat < 0.5:
                if char == key.ENTER and deltat < 0.3:
                    return self._return()
                self.last_key_count += 1
                times = repeat_times(self.last_key_count, deltat)
            else:
                self.last_key_count = 0
            if not handle_key(char, self, times):
                if len(char) > 1:
                    logger.warning(f"Skipping long character: {repr(char)} {char}")
                    continue
                self.write(char * times)
            self.last_key = char
            self.last_key_time = time()

    def save(self):
        self.history.save()


def repeat_times(times_repeated: int, deltat: float):
    factor = min(0.25/deltat, 4)
    return 1 if times_repeated <= 2 else round(min(times_repeated, 6)*factor)


def terminal_width() -> int:
    return shutil.get_terminal_size().columns


def line_count(lines: List[str]) -> int:
    """Return the number of lines in the list."""
    width = terminal_width()
    return sum([math.ceil(len(line) / width) for line in lines])


def terminal_lines(lines: Union[str,List[str]], width=terminal_width()) -> int:
    """Return the lines as they would be printed to the terminal."""
    if isinstance(lines, list):
        lines = "".join(lines)
    lines = lines.splitlines(True) or [""]
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
    last = new_lines[-1]
    if last.endswith("\n") or len(last) >= width:
        new_lines.append("")
    return new_lines or [""]


def handle_key(char: str, context: Context, count: int) -> None:
    history = context.history
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
        context.backspace(count)
        return True
    if char == key.DELETE:
        for _ in range(count):
            context.delete()
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
