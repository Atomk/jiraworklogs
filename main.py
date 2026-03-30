"""
=============================================================
Actitime → Jira Synchronizer
=============================================================

This script:
1. Fetches user's Actitime tasks for the current week
"""
from __future__ import annotations

import datetime
import json
import re
from dataclasses import dataclass

import requests


# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------

@dataclass
class Config:
    jira_domain: str
    jira_email: str
    jira_api_token: str
    actitime_domain: str
    actitime_basic_auth: str
    """API v1 supports only basic authentication."""

with open("config.json", encoding="utf-8") as f:
    CONFIG = Config(**json.load(f))


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


def actitime_task_name_to_jira_prefix(name: str) -> str | None:
    """
    Given the name of a task on Actitime, determines the name or the key of the
    corresponding work item on Jira. If the name is malformed or not handled,
    returns None.
    """
    if name.lower().startswith("meeting") or name.lower().startswith("sprint meeting"):
        # We use a single Jira item to track all meetings
        jira_prefix = "Meetings"
    elif match := re.match(r"ET-\d+", name):
        # Task key
        jira_prefix = match[0]
    else:
        jira_prefix = None
    return jira_prefix


# -------------------------------------------------------------------
# ACTITIME FUNCTIONS
# -------------------------------------------------------------------


def actitime_get_user_id() -> int:
    """Get user ID of the authenticated user."""

    url = f"{CONFIG.actitime_domain}/api/v1/users/me"
    headers = {"Authorization": f"Basic {CONFIG.actitime_basic_auth}"}

    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    return data["id"]


def actitime_get_timetrack(user_id: int, date_start: datetime.date) -> dict:
    """Get timetrack data for a specific user, from the specified date to now."""

    url = f"{CONFIG.actitime_domain}/api/v1/timetrack"
    headers = {"Authorization": f"Basic {CONFIG.actitime_basic_auth}"}

    params = {
        "userIds": user_id,
        "dateFrom": date_start.isoformat(), # first day, inclusive
        "stopAfter": 1000,
        "includeReferenced": "tasks", # include tasks data
    }
    resp = requests.get(url, params, headers=headers)
    resp.raise_for_status()
    return resp.json()


def actitime_print_timetrack(data: dict):
    weekday_name = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]
    tasks = data["tasks"]
    for day_info in data["data"]:
        date = datetime.date.fromisoformat(day_info["date"])
        weekday = weekday_name[date.weekday()]
        print(f"{date.strftime('%d %b %Y')}, {weekday}")

        total_minutes = 0
        for record in day_info["records"]:
            task_id = str(record["taskId"])
            minutes = record["time"]
            print(f"- {minutes} min \t {tasks[task_id]['name']}")
            total_minutes += minutes
        print(f"TOTAL: {total_minutes}")
        print()


# -------------------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------------------

def main():
    user_id = actitime_get_user_id()

    monday, sunday = get_start_end_of_current_week()
    timetrack = actitime_get_timetrack(user_id, monday)

    if not timetrack["data"]:
        # You cannot even get the added tasks if there's no time records
        print("ERROR: No data in timetrack for the current week.")
        return

    print("Actitime tasks with recorded time this week:")
    for _, task_data in timetrack["tasks"].items():
        task_name = task_data["name"]
        jira_prefix = actitime_task_name_to_jira_prefix(task_name) or "(none)"
        print(f"- {jira_prefix.ljust(12)} {task_name}")

    print()

    actitime_print_timetrack(timetrack)


if __name__ == "__main__":
    main()
