"""
=============================================================
Actitime → Jira Synchronizer
=============================================================

This script:
1. Fetches user's Actitime tasks for the current week
2. Fetches user's Jira tasks in currently active sprints
3. Compares tasks keys to ensure each Actitime task has a corresponding Jira task
4. Uploads worklogs to Jira for all matched tasks
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
from dataclasses import dataclass
from typing import TypedDict

import actitime
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
    actitime_domain: str
    actitime_basic_auth: str
    """API v1 supports only basic authentication."""
    actitime_ignore_tasks: list[str]

@dataclass
class CLIArgs:
    sync: bool
    sync_ignore_unmatched: bool
    view: str


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
    elif match := re.match(r"[A-Z][A-Z0-9_]+-[1-9][0-9]*", name):
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


# Inspired by actitime_print_timetrack
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


def jira_add_worklogs_from_actitime(
    jira_key: str,
    actitime_task_id: int,
    timetrack: actitime.ResponseTimetrack
):
    if str(actitime_task_id) not in timetrack["tasks"]:
        raise ValueError(f"actitime task id `{actitime_task_id}` not found in timetrack")

    for day in timetrack["data"]:
        worked_seconds = 0
        for record in day["records"]:
            if record["taskId"] == actitime_task_id:
                worked_seconds = record["time"] * 60
                break
        if worked_seconds <= 0:
            # no data for this task in this day
            continue

        # Endpoint errors say that datetimes must be in this format: yyyy-MM-dd'T'HH:mm:ss.SSSZ
        # But actually the timezone must be in +HHmm format (without the colon)

        # Create datetime in local timezone, convert to UTC, convert to ISO string.
        date = datetime.date.fromisoformat(day["date"])
        # 2026-03-30

        local_tz = datetime.datetime.now().astimezone().tzinfo
        date = datetime.datetime(
            date.year, date.month, date.day, 8, 1, tzinfo=local_tz
        ).astimezone(datetime.timezone.utc)
        # 2026-03-30T06:01:00+00:00
        # (intentionally setting 8:01 so on Jira you can see which logs were created via script)

        datetime_iso = date.isoformat(timespec="milliseconds").replace("+00:00", "+0000")
        # 2026-03-30T06:01:00.000+0000

        worklog: jira.WorklogCreate = {
            # TODO what happens if you submit two time the same?
            #   You have duplicated worklog. Should prevent submit if task already has worklogs
            "started": datetime_iso,
            "timeSpentSeconds": worked_seconds,
        }

        # TODO: document response type
        jira.add_worklog(jira_key, worklog)


# -------------------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------------------


def main_jira_view_worklogs():
    result = jira.get_tasks_current_sprint(worklogs=True)
    # FIXME dehardcode sprint start date
    date_start = datetime.date(2026, 5, 18)
    timetrack = jira_tasks_to_timetrack(result, date_start)
    jira_print_timetrack(timetrack)


def main(config: Config, args: CLIArgs):
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
        if actitask.name in config.actitime_ignore_tasks:
            continue

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
    if unmatched_jira_tasks:
        print("The following Jira tasks have no correspondence in Actitime's timetrack:")
        for key, title in unmatched_jira_tasks.items():
            print(f"- {key}: {title}")
        print()

    unmatched_actitime_tasks: list[ActitimeTask] = []
    for pair in pairings:
        if pair.jira_key is None:
            unmatched_actitime_tasks.append(acti_tasks[pair.acti_id])
    if unmatched_actitime_tasks:
        print("The following Actitime tasks have no correspondence in Jira's current sprint:")
        for actitask in unmatched_actitime_tasks:
            print("- %s [%s] \"%s\"" % (actitask.id, actitask.jira_matcher, actitask.name))
        print()

    if not args.sync:
        return
    if not args.sync_ignore_unmatched:
        if unmatched_actitime_tasks or unmatched_jira_tasks:
            print("You must fix the unmatched tasks before you can send time data to Jira")
            return

    # TODO allow to ignore some Actitime tasks (e.g. "Chores")

    # TODO prevent sending data to Jira for a task that already has worklogs for that day,
    #   otherwise running this script multiple times will create a copy of all worklogs again.
    #   In the future I may implement the possibility to update existing worklogs.

    # TODO raise error if Jira task has multiple worklogs for the same day, it may
    #  be an issue since Actitime has one record per task per day (in the timetrack at least,
    #  in the calendar I'm not sure but that's not supported anyway in API v1)

    for pair in pairings:
        if not pair.jira_key:
            continue
        jira_add_worklogs_from_actitime(pair.jira_key, int(pair.acti_id), timetrack)


if __name__ == "__main__":
    with open("config.json", encoding="utf-8") as f:
        CONFIG = Config(**json.load(f))

    actitime.init(CONFIG.actitime_domain, CONFIG.actitime_basic_auth)
    jira.init(CONFIG.jira_domain, CONFIG.jira_email, CONFIG.jira_api_token)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--sync',
        action="store_true",
        help="Whether to sync data, or view only.")
    parser.add_argument(
        '--sync-ignore-unmatched',
        action="store_true",
        help="Whether to sync data even if some Actitime tasks have no"
        " correspondence in the current Jira sprints, and vice versa.")
    # TODO this should not be allowed to be combined with the other two options.
    #  I played a bit with subparsers but haven't settled on what I like more,
    #  for now I'll just leave this option here.
    parser.add_argument(
        '--view',
        choices=["jira"],
        help="View logged hours.")
    parser.parse_args()
    args = CLIArgs(**parser.parse_args().__dict__)

    if args.view == "jira":
        main_jira_view_worklogs()
    else:
        main(CONFIG, args)
