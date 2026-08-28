from src.utils.spaced_repetition import schedule_next_review


def test_first_good_review_sets_interval_to_one_day():
    result = schedule_next_review(grade="good", ease_factor=2.5, interval_days=0, repetitions=0)
    assert result.interval_days == 1
    assert result.repetitions == 1


def test_second_good_review_sets_interval_to_six_days():
    first = schedule_next_review(grade="good", ease_factor=2.5, interval_days=0, repetitions=0)
    second = schedule_next_review(
        grade="good", ease_factor=first.ease_factor,
        interval_days=first.interval_days, repetitions=first.repetitions,
    )
    assert second.interval_days == 6
    assert second.repetitions == 2


def test_third_good_review_multiplies_by_ease_factor():
    r1 = schedule_next_review(grade="good", ease_factor=2.5, interval_days=0, repetitions=0)
    r2 = schedule_next_review(grade="good", ease_factor=r1.ease_factor, interval_days=r1.interval_days, repetitions=r1.repetitions)
    r3 = schedule_next_review(grade="good", ease_factor=r2.ease_factor, interval_days=r2.interval_days, repetitions=r2.repetitions)
    assert r3.interval_days == round(6 * r2.ease_factor)


def test_failing_a_card_resets_repetitions_and_interval():
    r1 = schedule_next_review(grade="good", ease_factor=2.5, interval_days=0, repetitions=0)
    r2 = schedule_next_review(grade="good", ease_factor=r1.ease_factor, interval_days=r1.interval_days, repetitions=r1.repetitions)
    failed = schedule_next_review(grade="again", ease_factor=r2.ease_factor, interval_days=r2.interval_days, repetitions=r2.repetitions)
    assert failed.repetitions == 0
    assert failed.interval_days == 1


def test_ease_factor_never_drops_below_1_3():
    ease = 1.3
    reps = 5
    interval = 10
    for _ in range(20):
        result = schedule_next_review(grade="again", ease_factor=ease, interval_days=interval, repetitions=reps)
        ease, interval, reps = result.ease_factor, result.interval_days, result.repetitions
    assert ease >= 1.3


def test_easy_grade_increases_ease_factor_more_than_good():
    good = schedule_next_review(grade="good", ease_factor=2.5, interval_days=6, repetitions=2)
    easy = schedule_next_review(grade="easy", ease_factor=2.5, interval_days=6, repetitions=2)
    assert easy.ease_factor > good.ease_factor
    assert easy.interval_days >= good.interval_days


def test_unknown_grade_raises():
    import pytest
    with pytest.raises(ValueError):
        schedule_next_review(grade="perfect", ease_factor=2.5, interval_days=0, repetitions=0)
