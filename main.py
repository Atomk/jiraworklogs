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

-------------------------------------------------------------
Configuration Required:
- JIRA_DOMAIN
- JIRA_EMAIL
- JIRA_API_TOKEN
- ACTITIME_DOMAIN
- ACTITIME_API_TOKEN
-------------------------------------------------------------
"""

import requests
import datetime
from collections import defaultdict
from dataclasses import dataclass, field

# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------

JIRA_DOMAIN = "https://yourcompany.atlassian.net"
JIRA_EMAIL = "your.email@company.com"
JIRA_API_TOKEN = "your_jira_api_token"

ACTITIME_DOMAIN = "https://yourcompany.actitime.com"
ACTITIME_BASIC_AUTH = "your_actitime_basic_auth"

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


def iso_date(dt):
    return dt.strftime("%Y-%m-%d")


# -------------------------------------------------------------------
# JIRA FUNCTIONS
# -------------------------------------------------------------------

def fetch_jira_worklogs_for_week(start_date: datetime.date, end_date: datetime.date):
    """
    Queries Jira for all work logs for the current user within this week.
    """
    jql = (
        f'worklogAuthor = currentUser() AND '
        f'worklogDate >= "{iso_date(start_date)}" AND worklogDate <= "{iso_date(end_date)}"'
    )

    url = f"{JIRA_DOMAIN}/rest/api/3/search"
    headers = {"Accept": "application/json"}
    params = {"jql": jql, "fields": "worklog,issuetype"}

    resp = requests.get(
        url,
        headers=headers,
        auth=(JIRA_EMAIL, JIRA_API_TOKEN),
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

def fetch_actitime_open_tasks():
    """
    Returns all open Actitime tasks the user can book time on.
    """
    url = f"{ACTITIME_DOMAIN}/api/v1/tasks"
    headers = {"Authorization": f"Basic {ACTITIME_BASIC_AUTH}"}

    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    tasks = resp.json()["items"]

    # Map Actitime tasks by their code (assuming task name IS the code, e.g., "ET‑432")
    return {t["name"]: t for t in tasks if t.get("status") == "OPEN"}


def post_actitime_time_entry(task_id, date, hours):
    """
    Sends a time entry to Actitime.
    """
    url = f"{ACTITIME_DOMAIN}/api/v1/time-entries"
    headers = {"Authorization": f"Basic {ACTITIME_BASIC_AUTH}", "Content-Type": "application/json"}

    payload = {
        "taskId": task_id,
        "date": iso_date(date),
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

    print(f"Fetching Jira worklogs from {iso_date(start)} to {iso_date(end)} ...")
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

if __name__ == "__main__":
    #sync_jira_to_actitime()
    fetch_actitime_open_tasks()
