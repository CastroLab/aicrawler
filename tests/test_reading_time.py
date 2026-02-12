from app.services.reading_time import estimate_reading_time


def test_short_article():
    assert estimate_reading_time(500) == 2


def test_medium_article():
    assert estimate_reading_time(2380) == 10


def test_zero_words():
    assert estimate_reading_time(0) == 1


def test_negative_words():
    assert estimate_reading_time(-100) == 1
