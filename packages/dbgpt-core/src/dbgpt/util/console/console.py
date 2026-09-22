"""Console utility functions for CLI."""

import dataclasses
import sys
from functools import lru_cache
from typing import Any, Callable, List, Optional, Tuple

from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.theme import Theme


@dataclasses.dataclass
class Output:
    """Output file."""

    title: str
    file: str


def _get_theme():
    return Theme(
        {
            "success": "green",
            "info": "bright_blue",
            "warning": "bright_yellow",
            "error": "red",
        }
    )


@lru_cache(maxsize=None)
def get_console(output: Output | None = None) -> Console:
    return Console(
        force_terminal=True,
        color_system="standard",
        theme=_get_theme(),
        file=output.file if output else None,
    )


# ---------------------------------------------------------------------------
# Terminal raw-mode helpers (stdlib only)
# ---------------------------------------------------------------------------


def _supports_raw_mode() -> bool:
    """Return True if stdin supports raw mode (TTY and termios available)."""
    if not sys.stdin.isatty():
        return False
    try:
        import termios  # noqa: F401
        import tty  # noqa: F401

        return True
    except ImportError:
        return False


def _read_key() -> str:
    """Read a single keypress from stdin in raw mode.

    Returns:
        str: One of ``'up'``, ``'down'``, ``'enter'``, or the raw character.

    Raises:
        KeyboardInterrupt: On Ctrl-C.
    """
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            ch2 = sys.stdin.read(1)
            ch3 = sys.stdin.read(1)
            if ch2 == "[":
                if ch3 == "A":
                    return "up"
                if ch3 == "B":
                    return "down"
            return ch
        if ch in ("\r", "\n"):
            return "enter"
        if ch == "\x03":
            raise KeyboardInterrupt
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _move_up(console: Console, lines: int) -> None:
    """Move terminal cursor up *lines* rows and clear those lines."""
    # ANSI: move up N lines then erase to end of screen
    console.file.write(f"\x1b[{lines}A\x1b[0J")
    console.file.flush()


class CliLogger:
    def __init__(self, output: Output | None = None):
        self.console = get_console(output)

    def success(self, msg: str, **kwargs):
        self.console.print(f"[success]{msg}[/]", **kwargs)

    def info(self, msg: str, **kwargs):
        self.console.print(f"[info]{msg}[/]", **kwargs)

    def warning(self, msg: str, **kwargs):
        self.console.print(f"[warning]{msg}[/]", **kwargs)

    def error(self, msg: str, exit_code: int = 0, **kwargs):
        self.console.print(f"[error]{msg}[/]", **kwargs)
        if exit_code != 0:
            sys.exit(exit_code)

    def debug(self, msg: str, **kwargs):
        self.console.print(f"[cyan]{msg}[/]", **kwargs)

    def print(self, *objects: Any, sep: str = " ", end: str = "\n", **kwargs):
        self.console.print(*objects, sep=sep, end=end, **kwargs)

    def markdown(self, msg: str, **kwargs):
        md = Markdown(msg)
        self.console.print(md, **kwargs)

    def ask(self, msg: str, **kwargs):
        return Prompt.ask(msg, **kwargs)

    def select(
        self,
        prompt: str,
        options: List[Tuple[str, str]],
        _read_key_fn: Optional[Callable[[], str]] = None,
    ) -> int:
        """Display an interactive arrow-key selector and return the chosen index.

        Args:
            prompt (str): Header text displayed above the option list.
            options (List[Tuple[str, str]]): Each tuple is (name, description).
                ``name`` is the display name rendered in bold.
                ``description`` is dim helper text shown after the name.
            _read_key_fn (Optional[Callable[[], str]]): Override the key-reading
                function (used for testing).  Should return one of: ``'up'``,
                ``'down'``, ``'enter'``, or a single character string.

        Returns:
            int: Zero-based index of the selected option.
        """
        read_key = _read_key_fn or _read_key

        # If raw-mode isn't available, fall back to numbered input.
        if not _supports_raw_mode():
            return self._select_fallback(prompt, options)

        current = 0
        n = len(options)

        self.console.print(f"\n  {prompt}\n")

        def _render(idx: int, move_up_lines: int = 0) -> None:
            buf = ""
            if move_up_lines > 0:
                buf += f"\x1b[{move_up_lines}A\x1b[0J"
            for i, (name, desc) in enumerate(options):
                if i == idx:
                    marker = "\x1b[1;96m●\x1b[0m"
                else:
                    marker = "\x1b[2m○\x1b[0m"
                bold_name = f"\x1b[1m{name}\x1b[0m"
                dim_desc = f"\x1b[2m{desc}\x1b[0m"
                buf += f"  {marker} {bold_name:<20}{dim_desc}\n"
            self.console.file.write(buf)
            self.console.file.flush()

        _render(current)

        while True:
            try:
                key = read_key()
            except KeyboardInterrupt:
                raise

            if key == "up":
                current = (current - 1) % n
                _render(current, move_up_lines=n)
            elif key == "down":
                current = (current + 1) % n
                _render(current, move_up_lines=n)
            elif key == "enter":
                _render(current, move_up_lines=n)
                self.console.print("")
                return current
            elif key.isdigit():
                num = int(key)
                if 1 <= num <= n:
                    current = num - 1
                    _render(current, move_up_lines=n)
                    self.console.print("")
                    return current

    def _select_fallback(
        self,
        prompt: str,
        options: List[Tuple[str, str]],
    ) -> int:
        """Numbered fallback for non-TTY environments."""
        self.console.print(f"\n  {prompt}\n")
        for i, (name, desc) in enumerate(options, start=1):
            self.console.print(
                f"  [[bold]{i}[/bold]] [bold]{name}[/bold]  [dim]{desc}[/dim]"
            )
        self.console.print("")
        while True:
            raw = Prompt.ask("Enter a number", default="1")
            try:
                choice = int(raw)
                if 1 <= choice <= len(options):
                    return choice - 1
            except (ValueError, TypeError):
                pass
            self.console.print(
                f"[warning]Please enter a number between 1 and {len(options)}.[/]"
            )
