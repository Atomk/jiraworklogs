"""
Jira REST API client.

Before use, call `init` providing it authorization data.
"""
from typing import TypedDict, Any

import requests
from requests.auth import HTTPBasicAuth


_BASE_URL: str
_BASIC_AUTH: HTTPBasicAuth


class Issue(TypedDict):
    expand: str
    """renderedFields,names,schema,operations,editmeta,changelog,versionedRepresentations"""
    id: str
    """43989"""
    self: str
    """https://vdagroup.atlassian.net/rest/api/3/issue/43989"""
    key: str
    """JJ-1504"""
    fields: dict[str, Any]
    """{"summary": "Meetings", "worklog": {}}"""


class ResponseSprint(TypedDict):
    issues: list[Issue]
    isLast: bool


class WorklogCreate(TypedDict):
    # NOTE: other fields are available, but these are the ones we care about
    started: str
    """"Required only on worklog creation, not on update.
    ISO format: 2021-01-17T12:34:00.000+0000"""
    timeSpentSeconds: int
    """The time in seconds spent working on the issue."""


def init(base_url: str, email: str, token: str):
    global _BASE_URL, _BASIC_AUTH
    _BASE_URL = base_url
    _BASIC_AUTH = HTTPBasicAuth(email, token)


def get_tasks_current_sprint(worklogs: bool = False) -> ResponseSprint:
    jql = "assignee = currentUser() AND sprint in openSprints() ORDER BY created DESC"
    return get_jql(jql, worklogs)


def get_jql(jql: str, worklogs: bool = False):
    url = f"{_BASE_URL}/rest/api/3/search/jql"
    headers = {"Accept": "application/json"}
    # No fields  -->  {'issues': [{'id': '43989'}, {'id': '43956'}, {'id': '43872'}], 'isLast': True}
    params = {"jql": jql, "fields": "summary"}
    if worklogs:
        params["fields"] += ",worklog"

    resp = requests.get(
        url,
        headers=headers,
        auth=_BASIC_AUTH,
        params=params
    )
    resp.raise_for_status()
    data = resp.json()
    return data


def add_worklog(task_key: str, data: WorklogCreate) -> dict:
    # you can pass an issue's ID or its key
    url = f"{_BASE_URL}/rest/api/3/issue/{task_key}/worklog"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    resp = requests.post(
        url,
        headers=headers,
        auth=_BASIC_AUTH,
        json=data,
    )
    resp.raise_for_status()
    data = resp.json()
    return data
