from __future__ import annotations

import argparse
import datetime
import json
from dataclasses import dataclass
from typing import TypedDict

import jira
import utils


# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------

@dataclass
class Config:
    jira_domain: str
    jira_email: str
    jira_api_token: str



# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------

def get_start_end_of_current_week() -> tuple[datetime.date, datetime.date]:
    """
    Return two `datetime.date` objects representing Monday and Sunday for the current week.
    """
    today = datetime.date.today()
    start = today - datetime.timedelta(days=today.weekday())
    end = start + datetime.timedelta(days=6)
    return start, end


# -------------------------------------------------------------------
# JIRA FUNCTIONS
# -------------------------------------------------------------------


class JiraTimetrackRecord(TypedDict):
    key: str
    """Jira key of the tasks associated to this time record."""
    time: int
    """Seconds worked on the task."""

class JiraTimetrack(TypedDict):
    """Represents Jira worklogs grouped by day.
    The structure is inspired by Actitime's timetrack format.
    """
    tasks: dict[str, str]
    """Associates task ID with its title."""
    data: dict[str, list[JiraTimetrackRecord]]
    """Associates an ISO date to a list of time records."""


def jira_tasks_to_timetrack(data: jira.ResponseSprint, date_start: datetime.date) -> JiraTimetrack:
    """Get Jira tasks for the current sprint and organize worklogs data in a
    dictionary that groups worked time by day.

    `date_start`: only show worklogs starting from this date.
    """
    timetrack: JiraTimetrack = {
        "tasks": {},
        "data": {},
    }
    for issue in data["issues"]:
        key = issue["key"]
        summary = issue["fields"]["summary"]
        timetrack["tasks"][key] = summary

        for worklog in issue["fields"]["worklog"]["worklogs"]:
            # TODO Jira uses a +hhmm notation for timezone offset, while Python accepts
            #   +hh:mm (adds colon), needs to be processed to convert it correctly.
            #   For now a workaround is to just strip the timezone part.
            started_iso = worklog["started"].split("+")[0]
            date_iso = worklog["started"].split("T")[0]
            worklog_start = datetime.datetime.fromisoformat(started_iso)
            if worklog_start.date() < date_start:
                # skip worklogs outside of the requested range. Tasks that were created in older sprints
                # may have worklogs created before the current sprint started.
                continue
            if date_iso not in timetrack["data"]:
                timetrack["data"][date_iso] = []
            timetrack["data"][date_iso].append({
                "key": key,
                "time": worklog['timeSpentSeconds'],
            })
    return timetrack


def jira_print_timetrack(timetrack: JiraTimetrack) -> None:
    weekday_name = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]
    tasks = timetrack["tasks"]
    ordered_dates = sorted(timetrack["data"].keys())
    if not tasks or not ordered_dates:
        print("no tasks or worklogs to print")
        return
    for date_iso in ordered_dates:
        date = datetime.date.fromisoformat(date_iso)
        weekday = weekday_name[date.weekday()]
        print(f"{date.strftime('%d %b %Y')}, {weekday}")

        total_minutes = 0
        for record in timetrack["data"][date_iso]:
            task_id = str(record["key"])
            minutes = record["time"] // 60
            print(f"- {utils.timefmt(minutes)} \t {tasks[task_id]}")
            total_minutes += minutes
        print(f"TOTAL: {utils.timefmt(total_minutes)}")
        print()


def jira_sprint_tasks_dictionary() -> dict[str, str]:
    """Returns a dict that maps Jira task keys to their summary (task title)."""
    result = jira.get_tasks_current_sprint()
    tasks = {}
    for issue in result["issues"]:
        key = issue["key"]
        summary = issue["fields"]["summary"]
        tasks[key] = summary
    return tasks


# -------------------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------------------


def main():
    result = jira.get_tasks_current_sprint(worklogs=True)
    # FIXME dehardcode sprint start date
    date_start = datetime.date(2026, 5, 18)
    timetrack = jira_tasks_to_timetrack(result, date_start)
    jira_print_timetrack(timetrack)


if __name__ == "__main__":
    with open("config.json", encoding="utf-8") as f:
        CONFIG = Config(**json.load(f))

    jira.init(CONFIG.jira_domain, CONFIG.jira_email, CONFIG.jira_api_token)

    main()
