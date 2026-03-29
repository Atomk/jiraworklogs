import datetime as dt
from unittest.mock import patch

import main


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

    # Other
    assert main.actitime_task_name_to_jira_prefix("Cleanup/rebase stale branches") is None
    assert main.actitime_task_name_to_jira_prefix("Daily tasks") is None
