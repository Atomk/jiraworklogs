import json
import re
import datetime as dt
from unittest.mock import patch, call

import pytest

import actitime
import main


@pytest.fixture(autouse=True)
def prevent_http_requests():
    with (
        patch("requests.request"),
        patch("requests.get"),
        patch("requests.post"),
    ):
        yield


@pytest.fixture
def timetrack() -> actitime.ResponseTimetrack:
    with open("test/actitime_timetrack.json") as f:
        return json.load(f)


def test_get_start_end_of_current_week():
    # `datetime.date.today` cannot be patched because it's actually a C library,
    # as a workaround we create a fake wrapper that can be modified.
    # https://williambert.online/2011/07/how-to-unit-testing-in-django-with-mocking-and-patching/
    class FakeDate(dt.date):
        @classmethod
        def today(cls):
            return fake_today

    fake_today = dt.date(2026, 3, 27)
    with patch("datetime.date", FakeDate):
        monday, sunday = main.get_start_end_of_current_week()
        assert monday == dt.date(2026, 3, 23)
        assert sunday == dt.date(2026, 3, 29)


def test_actitime_task_name_to_jira_prefix():
    # Meetings
    assert main.actitime_task_name_to_jira_prefix("Meetings") == "Meetings"
    assert main.actitime_task_name_to_jira_prefix("meeting scheduler") == "Meetings"
    assert main.actitime_task_name_to_jira_prefix("Sprint meetings") == "Meetings"
    assert main.actitime_task_name_to_jira_prefix("sprint meeting") == "Meetings"
    assert main.actitime_task_name_to_jira_prefix("strip meeting") is None

    # Jira work item keys
    assert main.actitime_task_name_to_jira_prefix("JJ-1489: new item encoder") == "JJ-1489"
    assert main.actitime_task_name_to_jira_prefix("JJ-1489 new item encoder") == "JJ-1489"
    assert main.actitime_task_name_to_jira_prefix("JJ 1489 new item encoder") is None
    assert main.actitime_task_name_to_jira_prefix("JJ1489 new item encoder") is None
    assert main.actitime_task_name_to_jira_prefix("ABRA-123") == "ABRA-123"
    assert main.actitime_task_name_to_jira_prefix("abra-123") is None
    assert main.actitime_task_name_to_jira_prefix("JJ-0") is None
    assert main.actitime_task_name_to_jira_prefix("JJ-00") is None
    assert main.actitime_task_name_to_jira_prefix("JJ-1") == "JJ-1"
    assert main.actitime_task_name_to_jira_prefix("J-1") is None

    # Other
    assert main.actitime_task_name_to_jira_prefix("Cleanup/rebase stale branches") is None
    assert main.actitime_task_name_to_jira_prefix("Daily tasks") is None


class TestJiraAddWorklogsFromActitime:
    def test_invalid_actitime_id(self, timetrack):
        msg = "actitime task id `1234` not found in timetrack"
        with pytest.raises(ValueError, match=re.escape(msg)):
            with patch("jira.add_worklog"):
                main.jira_add_worklogs_from_actitime("JJ-XXXX", 1234, timetrack)

    @pytest.mark.skip
    def test_invalid_jira_key(self, timetrack):
        # TODO: this involves making the jira.add_worklog return an error 404,
        #  I need to see what actually happens in this case. Or just don't detect this
        #  and instead handle generic 400/500 errors. In that case I should add
        #  a test for the case when uploading multiple worklogs but a few fail,
        #  block or continue and report errors?
        pass

    def test_single_worklog(self, timetrack):
        with patch("jira.add_worklog") as mock_add_worklog:
            main.jira_add_worklogs_from_actitime("JJ-XXXX", 7895, timetrack)
        assert mock_add_worklog.call_args_list == [
            call('JJ-XXXX', {'started': '2026-03-25T06:01:00.000+0000', 'timeSpentSeconds': 2400})
        ]

    def test_multiple_worklogs(self, timetrack):
        with patch("jira.add_worklog") as mock_add_worklog:
            main.jira_add_worklogs_from_actitime("JJ-XXXX", 8545, timetrack)
        assert mock_add_worklog.call_args_list == [
            call('JJ-XXXX', {'started': '2026-03-25T06:01:00.000+0000', 'timeSpentSeconds': 12000}),
            call('JJ-XXXX', {'started': '2026-03-27T06:01:00.000+0000', 'timeSpentSeconds': 1800}),
        ]
