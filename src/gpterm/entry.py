
import os
from typing import List

import atexit
import readline
from dotenv import load_dotenv
from getch import getch, getche

load_dotenv()
history_file = os.getenv("GPTERM_HISTORY_FILE", "./gpterm_history")
history_size = int(os.getenv("GPTERM_HISTORY_SIZE", "-1"))

try:
    readline.read_history_file(history_file)
    history_length = readline.get_current_history_length()
except FileNotFoundError:
    history_length = 0
    open(history_file, "a").close()

def save_history(history_file: str = history_file, prev_history_length = 0) -> None:
    """Save the readline history to a file."""
    new_history_length = readline.get_current_history_length()
    readline.set_history_length(history_size)
    readline.append_history_file(new_history_length - prev_history_length, history_file)

atexit.register(save_history, history_file, history_length)

def pchar(char: str) -> None:
    """Print a character without a newline."""
    print(char, end="", flush=True)

def get_input(prompt: str = "> ") -> str:
    entry = get_raw_input(prompt)
    entry = replace_files_with_contents(entry)
    return entry

def get_raw_input(prompt: str = "> ") -> str:
    """Read multi-line input from the user until a non-trailing space line is entered."""
    # print(prompt, end="", flush=True)
    lines: List[str] = []
    while True:
        line = input(prompt)
        # while not line.endswith("\n"):
        #     try:
        #         char = getche()
        #     except EOFError:
        #         print("\nGoodbye.")
        #         exit(0)
        #     line += char
        #     # pchar(char)
        #     # print(ord(char))
        lines.append(line.rstrip())
        if not line.endswith(" "):
            return "\n".join(lines)

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