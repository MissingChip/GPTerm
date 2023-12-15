
import sys
import termios
from readchar import key

ESCAPE = "\x1b"
SHIFT_UP = "\x1b[1;2A"
SHIFT_DOWN = "\x1b[1;2B"
SHIFT_TAB = "\x1b[Z"

key.SHIFT_UP = SHIFT_UP
key.SHIFT_DOWN = SHIFT_DOWN
key.SHIFT_TAB = SHIFT_TAB

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
    if c2 not in "0[":
        return c1 + c2

    if c2 == '[':
        c3 = readchar()
        while ord(c3[-1]) < 0x40:
            c3 += readchar()
        return c1 + c2 + c3

    c3 = readchar()
    if c3 not in "12345":
        return c1 + c2 + c3

    c4 = readchar()
    if c4 not in "123456789;":
        return c1 + c2 + c3 + c4

    c5 = readchar()
    return c1 + c2 + c3 + c4 + c5