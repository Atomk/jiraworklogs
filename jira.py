"""
Jira REST API client.

Before use, call `init` providing it authorization data.
"""
from typing import TypedDict

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
    fields: dict[str, str]
    """{"summary": "Meetings"}"""


class ResponseSprint(TypedDict):
    issues: list[Issue]
    isLast: bool


def init(base_url: str, email: str, token: str):
    global _BASE_URL, _BASIC_AUTH
    _BASE_URL = base_url
    _BASIC_AUTH = HTTPBasicAuth(email, token)


def get_tasks_current_sprint() -> ResponseSprint:
    jql = "assignee = currentUser() AND sprint in openSprints() ORDER BY created DESC"

    url = f"{_BASE_URL}/rest/api/3/search/jql"
    headers = {"Accept": "application/json"}
    # No fields  -->  {'issues': [{'id': '43989'}, {'id': '43956'}, {'id': '43872'}], 'isLast': True}
    params = {"jql": jql, "fields": "summary"}

    resp = requests.get(
        url,
        headers=headers,
        auth=_BASIC_AUTH,
        params=params
    )
    resp.raise_for_status()
    data = resp.json()
    return data
