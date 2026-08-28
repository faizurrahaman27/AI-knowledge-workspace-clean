"""
SM-2 spaced-repetition scheduling -- the algorithm SuperMemo 2 introduced
in 1987 and Anki's default scheduler is still based on. Not a novel
algorithm invented for this project; this is a direct implementation of
the published formula: https://en.wikipedia.org/wiki/SuperMemo#Description_of_SM-2_algorithm

Quality is graded 0-5 in the original paper; this app exposes a simpler
four-button UI (Again/Hard/Good/Easy) and maps it to the equivalent
quality scores below, since most spaced-repetition apps (Anki included)
found the full 0-5 scale more granular than users actually want.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

GRADE_TO_QUALITY = {
    "again": 0,
    "hard": 3,
    "good": 4,
    "easy": 5,
}


@dataclass
class ScheduleResult:
    ease_factor: float
    interval_days: int
    repetitions: int
    due_at: datetime


def schedule_next_review(
    grade: str,
    ease_factor: float,
    interval_days: int,
    repetitions: int,
) -> ScheduleResult:
    if grade not in GRADE_TO_QUALITY:
        raise ValueError(f"Unknown grade '{grade}'. Must be one of {list(GRADE_TO_QUALITY)}.")

    quality = GRADE_TO_QUALITY[grade]

    if quality < 3:
        # Failed recall: reset the repetition streak and review again
        # tomorrow, but DON'T reset ease_factor -- a single lapse
        # shouldn't erase how well-learned the card generally is.
        repetitions = 0
        interval_days = 1
    else:
        if repetitions == 0:
            interval_days = 1
        elif repetitions == 1:
            interval_days = 6
        else:
            interval_days = round(interval_days * ease_factor)
        repetitions += 1

    # The SM-2 ease-factor update formula, clamped at a 1.3 floor so a
    # card never spirals down to near-zero intervals forever.
    ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ease_factor = max(1.3, ease_factor)

    due_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=interval_days)

    return ScheduleResult(
        ease_factor=round(ease_factor, 2),
        interval_days=interval_days,
        repetitions=repetitions,
        due_at=due_at,
    )
