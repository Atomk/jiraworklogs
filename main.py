"""
=============================================================
Jira → Actitime Synchronizer
=============================================================

This script:
1. Fetches all Jira worklogs for the current week.
2. Aggregates hours by:
   - Day
   - Jira ticket (issue key)
   - Category (e.g., Bug, Story, Task)
3. Fetches Actitime open tasks
4. Compares Jira tasks (with hours) vs Actitime task codes
5. Reports all missing hours to Actitime using the Actitime API
6. Logs results for transparency
"""
from __future__ import annotations

import datetime
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field

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
# DATA MODELS
# -------------------------------------------------------------------

@dataclass
class DayLog:
    date: datetime.date
    issue_key: str
    category: str
    hours: float


@dataclass
class WeekLogs:
    days: list = field(default_factory=list)

    def add(self, log: DayLog):
        self.days.append(log)

    def aggregate_by_issue(self):
        result = defaultdict(float)
        for log in self.days:
            result[log.issue_key] += log.hours
        return result


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
# JIRA FUNCTIONS
# -------------------------------------------------------------------

def fetch_jira_worklogs_for_week(start_date: datetime.date, end_date: datetime.date):
    """
    Queries Jira for all work logs for the current user within this week.
    """
    jql = (
        f'worklogAuthor = currentUser() AND '
        f'worklogDate >= "{start_date.isoformat()}" AND worklogDate <= "{end_date.isoformat()}"'
    )

    url = f"{CONFIG.jira_domain}/rest/api/3/search"
    headers = {"Accept": "application/json"}
    params = {"jql": jql, "fields": "worklog,issuetype"}

    resp = requests.get(
        url,
        headers=headers,
        auth=(CONFIG.jira_email, CONFIG.jira_api_token),
        params=params
    )
    resp.raise_for_status()
    data = resp.json()

    week_logs = WeekLogs()

    for issue in data.get("issues", []):
        issue_key = issue["key"]
        category = issue["fields"]["issuetype"]["name"]
        worklogs = issue["fields"].get("worklog", {}).get("worklogs", [])

        for wl in worklogs:
            started = wl["started"][:10]  # first 10 chars = YYYY-MM-DD
            log_date = datetime.date.fromisoformat(started)

            if start_date <= log_date <= end_date:
                seconds = wl["timeSpentSeconds"]
                hours = round(seconds / 3600, 2)
                week_logs.add(DayLog(log_date, issue_key, category, hours))

    return week_logs


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


def print_timetrack(data: dict):
    weekday_name = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]
    tasks = data["tasks"]
    for day_info in data["data"]:
        date = datetime.date.fromisoformat(day_info["date"])
        weekday = weekday_name[date.weekday()]
        print(f"{date.strftime('%d %b %Y')}, {weekday}")
        for record in day_info["records"]:
            task_id = str(record["taskId"])
            minutes = record["time"]
            print(f"- {minutes} min \t {tasks[task_id]['name']}")


def post_actitime_time_entry(task_id, date: datetime.date, hours):
    """
    Sends a time entry to Actitime.
    """
    url = f"{CONFIG.actitime_domain}/api/v1/time-entries"
    headers = {"Authorization": f"Basic {CONFIG.actitime_basic_auth}", "Content-Type": "application/json"}

    payload = {
        "taskId": task_id,
        "date": date.isoformat(),
        "duration": int(hours * 60),  # minutes
        "billable": True
    }

    resp = requests.post(url, json=payload, headers=headers)
    resp.raise_for_status()


# -------------------------------------------------------------------
# MAIN SYNC LOGIC
# -------------------------------------------------------------------

def sync_jira_to_actitime():
    # 1. Time range
    start, end = get_start_end_of_current_week()

    print(f"Fetching Jira worklogs from {start.isoformat()} to {end.isoformat()} ...")
    week_logs = fetch_jira_worklogs_for_week(start, end)

    # 2. Fetch Actitime open tasks
    actitime_tasks = fetch_actitime_open_tasks()
    actitime_codes = set(actitime_tasks.keys())

    # 3. Identify Jira tasks with hours
    jira_issue_hours = week_logs.aggregate_by_issue()

    print("\nValidating task presence in Actitime...")

    missing_tasks = [key for key in jira_issue_hours if key not in actitime_codes]

    if missing_tasks:
        print("⚠️ Missing Actitime tasks:")
        for m in missing_tasks:
            print(f" - {m}")
        print("You must create these tasks in Actitime before syncing.\n")

    # 4. Send hours to Actitime (only for tasks that exist)
    print("Reporting time to Actitime...")

    for log in week_logs.days:
        if log.issue_key not in actitime_codes:
            continue  # skip missing tasks

        task_id = actitime_tasks[log.issue_key]["id"]
        print(f" → Reporting {log.hours}h on {log.issue_key} for {log.date}")

        post_actitime_time_entry(task_id, log.date, log.hours)

    print("\n✅ Sync complete!")


# -------------------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------------------

def main():
    user_id = actitime_get_user_id()

    monday, sunday = get_start_end_of_current_week()
    timetrack = actitime_get_timetrack(user_id, monday)

    print("Actitime tasks with recorded time this week:")
    for _, task_data in timetrack["tasks"].items():
        task_name = task_data["name"]
        jira_prefix = actitime_task_name_to_jira_prefix(task_name) or "(none)"
        print(f"- {jira_prefix.ljust(12)} {task_name}")

    print()

    print_timetrack(timetrack)


if __name__ == "__main__":
    main()
