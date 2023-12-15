
import sys
import termios
from readchar import key

def init_chario():
    fd = sys.stdin.fileno()
    term = termios.tcgetattr(fd)
    term[3] &= ~(termios.ICANON | termios.ECHO | termios.IGNBRK | termios.BRKINT)
    termios.tcsetattr(fd, termios.TCSAFLUSH, term)

def readchar() -> str:
    """Reads a single character from the input stream.
    Blocks until a character is available."""
    return sys.stdin.read(1)


def readkey() -> str:
    """Get a keypress. If an escaped key is pressed, the full sequence is
    read and returned as noted in `_posix_key.py`."""

    c1 = readchar()

    if c1 in [key.CTRL_C]:
        raise KeyboardInterrupt

    if c1 != "\x1B":
        return c1

    c2 = readchar()
    if c2 not in "\x4F\x5B":
        return c1 + c2

    c3 = readchar()
    if c3 not in "\x31\x32\x33\x35\x36":
        return c1 + c2 + c3

    c4 = readchar()
    if c4 not in "\x30\x31\x33\x34\x35\x37\x38\x39":
        return c1 + c2 + c3 + c4

    c5 = readchar()
    return c1 + c2 + c3 + c4 + c5