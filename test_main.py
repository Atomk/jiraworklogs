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
