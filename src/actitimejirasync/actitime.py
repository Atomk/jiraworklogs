
"""
Actitime REST API client.

Before use, call `init` providing it authorization data.
"""
from __future__ import annotations

import datetime
from typing import TypedDict


import requests


_API_BASE_URL: str
_BASIC_AUTH: str


# -------------------------------------------------------------------
# MODELS
# -------------------------------------------------------------------


class Task(TypedDict):
    id: int
    name: str
    description: str
    created: int
    status: str
    workflowStatusId: int
    typeOfWorkId: int
    url: str
    projectName: str
    customerName: str
    workflowStatusName: str
    typeOfWorkName: str
    allowedActions: dict
    deadline: str | None
    estimatedTime: int | None
    customerId: int
    projectId: int


class ResponseTimetrackDayRecord(TypedDict):
    taskId: int
    time: int
    """Recorded time in minutes."""


class ResponseTimetrackDay(TypedDict):
    """Collects time recorded by a user on a specific day."""
    userId: int
    records: list[ResponseTimetrackDayRecord]
    dayOffset: int
    date: str
    """Date in YYYY-MM-DD format. Date that records refers to."""


class ResponseTimetrack(TypedDict):
    """Represents time records submitted betwen two dates."""
    dateFrom: str
    """Date in YYYY-MM-DD format."""
    dateTo: str
    """Date in YYYY-MM-DD format."""
    tasks: dict[str, Task]
    """WARNING: this field will not exist if `data` is empty."""
    data: list[ResponseTimetrackDay]


# -------------------------------------------------------------------
# FUNCTIONS
# -------------------------------------------------------------------


def init(base_url: str, basic_auth: str):
    global _API_BASE_URL, _BASIC_AUTH
    _API_BASE_URL = base_url
    _BASIC_AUTH = basic_auth


def get_user_id() -> int:
    """Get user ID of the authenticated user."""

    url = f"{_API_BASE_URL}/api/v1/users/me"
    headers = {"Authorization": f"Basic {_BASIC_AUTH}"}

    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    return data["id"]


def get_timetrack(user_id: int, date_start: datetime.date) -> ResponseTimetrack:
    """Get timetrack data for a specific user, from the specified date to now."""

    url = f"{_API_BASE_URL}/api/v1/timetrack"
    headers = {"Authorization": f"Basic {_BASIC_AUTH}"}

    params = {
        "userIds": user_id,
        "dateFrom": date_start.isoformat(), # first day, inclusive
        "stopAfter": 1000,
        "includeReferenced": "tasks", # include tasks data
    }
    resp = requests.get(url, params, headers=headers)
    resp.raise_for_status()
    return resp.json()
