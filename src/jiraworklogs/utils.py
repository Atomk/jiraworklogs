import shutil
import datetime
import os
import subprocess
import sys


class Colors:
    """ANSI sequences to color text in the terminal.
    Text to be styled should be put between a color sequence and ENDC.

    >>> print(f"this is {Colors.BLUE}styled{Colors.ENDC} text.")
    """
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    GRAY = '\033[90m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def get_start_end_of_current_week() -> tuple[datetime.date, datetime.date]:
    """
    Return two `datetime.date` objects representing Monday and Sunday for the current week.
    """
    today = datetime.date.today()
    start = today - datetime.timedelta(days=today.weekday())
    end = start + datetime.timedelta(days=6)
    return start, end


def timefmt(minutes: int) -> str:
    """Converts an amount of minutes into a duration string like this:
    - 60 -> "1h"
    - 90 -> "1h 30m"
    """
    if minutes < 0:
        raise ValueError("number of minutes must be positive")
    hours, mins = divmod(minutes, 60)
    if hours == 0:
        return f"{mins}m"
    elif mins == 0:
        return f"{hours}h"
    else:
        return f"{hours}h {mins}m"


def open_file_with_text_editor(path: str) -> None:
    if sys.platform == "linux":
        exit_code = None
        for command in ("xdg-open", "nano"):
            if shutil.which(command):
                exit_code = subprocess.call(["nano", path])
                if exit_code != 0:
                    raise Exception(f"subprocess exited with code {exit_code}.")
        if exit_code is None:
            raise Exception(f"could not find any available editor")
    elif os.name == "nt":
        # Emulate double-clicking on the file. Note that unlike subprocesses,
        # this immediately returns, without waiting for the application to close.
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.call(["open", path])
    else:
        raise Exception(f"unsupported platform: {sys.platform}")
