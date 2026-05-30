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
