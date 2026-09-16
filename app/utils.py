from datetime import datetime, date


def pct(value, total):
    if not total:
        return 0
    return round((value / total) * 100, 1)


def format_dt(value):
    if isinstance(value, datetime):
        return value.strftime("%d %b %Y, %I:%M %p")
    if isinstance(value, date):
        return value.strftime("%d %b %Y")
    return value
