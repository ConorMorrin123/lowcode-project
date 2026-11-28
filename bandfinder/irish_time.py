"""Irish time for Band Finder.

The database always stores times in UTC (that is what db.now() and SQLite's
datetime('now') give). People in Ireland think in Irish time, which is:
  * UTC in winter (GMT)
  * UTC + 1 hour in summer (IST, Irish Standard Time)
Summer time starts at 01:00 UTC on the last Sunday of March and ends at
01:00 UTC on the last Sunday of October (the EU rule Ireland follows).

Every "what day is it" or "show this date" question in the app goes through
this file, so local time and UTC are never mixed up.

Python's zoneinfo needs extra time zone data on Windows, so the rule is
written out here instead of adding a library.
"""
from datetime import date, datetime, time, timedelta, timezone

FORMAT = "%Y-%m-%d %H:%M:%S"   # the same text format the database uses
ONE_HOUR = timedelta(hours=1)


def last_sunday(year, month):
    """The date of the last Sunday in a month (March or October here)."""
    day = date(year, month + 1, 1) - timedelta(days=1)   # last day of the month
    return day - timedelta(days=(day.weekday() + 1) % 7)  # Monday=0 ... Sunday=6


def is_summer_time(utc_moment):
    """True if Ireland is on summer time (UTC+1) at this UTC moment."""
    year = utc_moment.year
    starts = datetime.combine(last_sunday(year, 3), time(1, 0))
    ends = datetime.combine(last_sunday(year, 10), time(1, 0))
    return starts <= utc_moment.replace(tzinfo=None) < ends


def utc_to_irish(utc_moment):
    """Turn a UTC datetime into Irish local time."""
    utc_moment = utc_moment.replace(tzinfo=None)
    return utc_moment + ONE_HOUR if is_summer_time(utc_moment) else utc_moment


def irish_to_utc(irish_moment):
    """Turn an Irish local datetime into UTC."""
    guess = irish_moment - ONE_HOUR
    return guess if is_summer_time(guess) else irish_moment


def now_in_ireland(utc_moment=None):
    """The current Irish local time."""
    if utc_moment is None:
        utc_moment = datetime.now(timezone.utc)
    return utc_to_irish(utc_moment)


def today(utc_moment=None):
    """Today's date in Ireland (not on the server's clock, not in UTC)."""
    return now_in_ireland(utc_moment).date()


def end_of_day_utc(irish_day):
    """23:59:59 Irish time on a given date, as UTC text for the database."""
    return irish_to_utc(datetime.combine(irish_day, time(23, 59, 59))).strftime(FORMAT)


def irish_date_of(utc_text):
    """The Irish date of a UTC timestamp stored in the database."""
    return utc_to_irish(datetime.strptime(utc_text[:19], FORMAT)).date()
