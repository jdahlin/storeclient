import datetime
from typing import Optional


def parse_datetime(s: Optional[str]) -> datetime.datetime:
    if s is None:
        return None
    try:
        dt = datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f%z")
    except ValueError:
        dt = datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f")
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt
