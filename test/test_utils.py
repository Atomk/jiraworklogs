import datetime as dt
from unittest.mock import patch

import pytest

from jiraworklogs import utils


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
        monday, sunday = utils.get_start_end_of_current_week()
        assert monday == dt.date(2026, 3, 23)
        assert sunday == dt.date(2026, 3, 29)


def test_timefmt():
    with pytest.raises(ValueError):
        utils.timefmt(-1)

    assert utils.timefmt(0) == "0m"
    assert utils.timefmt(59) == "59m"
    assert utils.timefmt(60) == "1h"
    assert utils.timefmt(61) == "1h 1m"
    assert utils.timefmt(119) == "1h 59m"
    assert utils.timefmt(120) == "2h"
