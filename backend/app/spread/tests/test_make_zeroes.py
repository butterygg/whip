from backend.app.spread.helpers import make_zeroes


def test_set_zeroes():
    zeroes_series = make_zeroes(
        "2021-01-01",
        "2021-01-05",
    )
    assert all(zeroes_series.values == [0, 0, 0, 0, 0])
    assert [str(v)[:10] for v in zeroes_series.index.values] == [
        "2021-01-01",
        "2021-01-02",
        "2021-01-03",
        "2021-01-04",
        "2021-01-05",
    ]


def test_empty():
    assert make_zeroes("2021-01-02", "2021-01-01").empty
