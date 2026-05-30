import pytest

from actitimejirasync import utils


def test_timefmt():
    with pytest.raises(ValueError):
        utils.timefmt(-1)

    assert utils.timefmt(0) == "0m"
    assert utils.timefmt(59) == "59m"
    assert utils.timefmt(60) == "1h"
    assert utils.timefmt(61) == "1h 1m"
    assert utils.timefmt(119) == "1h 59m"
    assert utils.timefmt(120) == "2h"
