"""
=============================================================
Actitime → Jira Synchronizer
=============================================================

This script:
1. Fetches user's Actitime tasks for the current week
2. Fetches user's Jira tasks in currently active sprints
3. Compares tasks keys to ensure each Actitime task has a corresponding Jira task
"""
from __future__ import annotations

import datetime
import json
import re
from dataclasses import dataclass

import actitime
import jira


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

def actitime_print_timetrack(data: actitime.ResponseTimetrack) -> None:
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
# JIRA FUNCTIONS
# -------------------------------------------------------------------

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
    user_id = actitime.get_user_id()

    monday, sunday = get_start_end_of_current_week()
    timetrack = actitime.get_timetrack(user_id, monday)

    if not timetrack["data"]:
        # You cannot even get the added tasks if there's no time records
        print("ERROR: No data in timetrack for the current week.")
        return

    @dataclass
    class ActitimeTask:
        id: str
        name: str
        jira_matcher: str

    print("Actitime tasks with recorded time this week:")
    acti_tasks: dict[str, ActitimeTask] = {}
    for task_id, task_data in timetrack["tasks"].items():
        task_name = task_data["name"]
        jira_prefix = actitime_task_name_to_jira_prefix(task_name) or "(none)"
        acti_tasks[task_id] = ActitimeTask(task_id, task_name, jira_prefix)
        print(f"- {jira_prefix.ljust(12)} {task_name}")

    print()

    actitime_print_timetrack(timetrack)

    @dataclass
    class Pairing:
        acti_id: str
        jira_key: str | None

    pairings: list[Pairing] = []

    jira_tasks = jira_sprint_tasks_dictionary()
    found_jira_keys = set()
    for _, actitask in acti_tasks.items():
        found_jira_key = None
        # If the Actitime task directly references a Jira task key (in the current sprint)
        if actitask.jira_matcher in jira_tasks:
            found_jira_key = actitask.jira_matcher
        else:
            # Instead of looking for a Jira key, look for a Jira tasks whose name
            # starts with the Actitime task matcher string.
            # TODO what if there's multiple "meetings" Jira issues? This loop could potentially
            #  match more than one task, stopping it early may choose the wrong task randomly
            prefix = actitask.jira_matcher.lower()
            for jkey, jname in jira_tasks.items():
                if jname.strip().lower().startswith(prefix):
                    found_jira_key = jkey
                    break

        pairings.append(Pairing(actitask.id, found_jira_key))
        if found_jira_key:
            found_jira_keys.add(found_jira_key)

    unmatched_jira_tasks = {k: v for k, v in jira_tasks.items() if k not in found_jira_keys}
    print("The following Jira tasks have no correspondence in Actitime:")
    for key, title in unmatched_jira_tasks.items():
        print(f"- {key}: {title}")
    print()

    print("The following Actitime tasks have no correspondence in Jira's current sprint:")
    for pair in pairings:
        if pair.jira_key is None:
            actitask = acti_tasks[pair.acti_id]
            print("- %s [%s] \"%s\"" % (actitask.id, actitask.jira_matcher, actitask.name))
    print()


if __name__ == "__main__":
    actitime.init(CONFIG.actitime_domain, CONFIG.actitime_basic_auth)
    jira.init(CONFIG.jira_domain, CONFIG.jira_email, CONFIG.jira_api_token)

    main()
