import datetime as dt
import json
from unittest.mock import patch

import pytest

from jiraworklogs import main


@pytest.fixture(autouse=True)
def prevent_http_requests():
    with (
        patch("requests.request"),
        patch("requests.get"),
        patch("requests.post"),
    ):
        yield


class TestJiraTasksToTImeTrack:
    @pytest.fixture(scope="class")
    def tasks_data(self):
        with open("test/jira_tasks_with_worklogs.json") as f:
            tasks_json = json.load(f)
        return tasks_json

    def test_start_date_is_first_day_with_worklogs(self, tasks_data):
        with open("test/jira_tasks_with_worklogs_timetrack.json") as f:
            expected = json.load(f)

        start_date = dt.date(2026, 9, 14)
        result = main.jira_tasks_to_timetrack(tasks_data, start_date)
        assert result == expected

    def test_start_date_is_last_day_with_worklogs(self, tasks_data):
        start_date = dt.date(2026, 9, 18)
        result = main.jira_tasks_to_timetrack(tasks_data, start_date)
        # TODO shouldn't this contain only the 5 tasks mentioned in records?
        assert len(result["tasks"]) == 13
        assert result["data"] == {
            "2026-09-18": [
                {"key": "JJ-2066", "time": 9000, "comment": ""},
                {"key": "JJ-2029", "time": 3900, "comment": "Commissioning meeting 2, clarify last stuff with Loren"},
                {"key": "JJ-1985", "time": 900, "comment": "Update config with A. and ensure it works"},
                {"key": "JJ-1486", "time": 3600, "comment": "lecture 1 + notes"},
                {"key": "JJ-1259", "time": 7200, "comment": "Continue implementation and try to fix tests by patching system date"},
            ],
        }

    def test_start_date_is_after_last_day_with_worklogs(self, tasks_data):
        start_date = dt.date(2026, 10, 1)
        result = main.jira_tasks_to_timetrack(tasks_data, start_date)
        # TODO shouldn't this contain zero tasks since there's no records?
        assert len(result["tasks"]) == 13
        assert len(result["data"]) == 0
