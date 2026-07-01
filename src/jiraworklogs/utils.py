import datetime


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
