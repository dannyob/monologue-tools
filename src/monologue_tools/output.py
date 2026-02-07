"""Terminal output utilities for monologue tools."""

import sys


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    BLUE = "\033[34m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"


def hyperlink(url, text=None):
    """Create OSC 8 terminal hyperlink."""
    if text is None:
        text = url
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


def print_status(emoji, message, color=Colors.RESET, file=None):
    """Print formatted status message to stderr."""
    if file is None:
        file = sys.stderr
    print(f"{color}{emoji} {message}{Colors.RESET}", file=file)


def print_info(message):
    print_status("ℹ️", message, Colors.CYAN)


def print_success(message):
    print_status("✅", message, Colors.GREEN)


def print_warning(message):
    print_status("⚠️", message, Colors.YELLOW)


def print_error(message):
    print_status("❌", message, Colors.RED)


def print_processing(message):
    print_status("⚙️", message, Colors.BLUE)
