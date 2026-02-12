WPM = 238


def estimate_reading_time(word_count: int) -> int:
    if word_count <= 0:
        return 1
    minutes = max(1, round(word_count / WPM))
    return minutes
