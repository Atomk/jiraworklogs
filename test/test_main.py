import datetime as dt
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
