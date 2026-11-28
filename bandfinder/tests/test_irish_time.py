"""Tests for Irish time (Week 3 review fix: no more mixing local time and UTC).

Run from the lowcode-project folder:
    .venv\\Scripts\\python.exe -m unittest discover -s bandfinder/tests -v
"""
import os
import sys
import unittest
from datetime import date, datetime, timedelta

BANDFINDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BANDFINDER)
os.environ.setdefault("SECRET_KEY", "test-only-not-a-real-secret")

import irish_time  # noqa: E402
from test_app import AppTestCase  # noqa: E402

import app as app_module  # noqa: E402
import db  # noqa: E402


class TestSummerTimeRule(unittest.TestCase):

    def test_last_sundays_of_2026(self):
        self.assertEqual(irish_time.last_sunday(2026, 3), date(2026, 3, 29))
        self.assertEqual(irish_time.last_sunday(2026, 10), date(2026, 10, 25))

    def test_summer_time_starts_at_1am_utc_on_last_sunday_of_march(self):
        self.assertFalse(irish_time.is_summer_time(datetime(2026, 3, 29, 0, 59)))
        self.assertTrue(irish_time.is_summer_time(datetime(2026, 3, 29, 1, 0)))

    def test_summer_time_ends_at_1am_utc_on_last_sunday_of_october(self):
        self.assertTrue(irish_time.is_summer_time(datetime(2026, 10, 25, 0, 59)))
        self.assertFalse(irish_time.is_summer_time(datetime(2026, 10, 25, 1, 0)))

    def test_winter_and_summer(self):
        self.assertFalse(irish_time.is_summer_time(datetime(2026, 1, 15, 12, 0)))
        self.assertTrue(irish_time.is_summer_time(datetime(2026, 7, 15, 12, 0)))


class TestIrishDates(unittest.TestCase):

    def test_late_summer_evening_in_utc_is_already_tomorrow_in_ireland(self):
        # 23:30 UTC on 15 July is 00:30 on 16 July in Ireland.
        self.assertEqual(irish_time.today(datetime(2026, 7, 15, 23, 30)), date(2026, 7, 16))
        self.assertEqual(irish_time.irish_date_of("2026-07-15 23:30:00"), date(2026, 7, 16))

    def test_winter_irish_date_matches_utc(self):
        self.assertEqual(irish_time.today(datetime(2026, 1, 15, 23, 30)), date(2026, 1, 15))
        self.assertEqual(irish_time.irish_date_of("2026-01-15 23:30:00"), date(2026, 1, 15))

    def test_end_of_irish_day_in_utc(self):
        # Summer: 23:59:59 Irish time is 22:59:59 UTC. Winter: the same.
        self.assertEqual(irish_time.end_of_day_utc(date(2026, 7, 15)), "2026-07-15 22:59:59")
        self.assertEqual(irish_time.end_of_day_utc(date(2026, 1, 15)), "2026-01-15 23:59:59")

    def test_pages_show_the_irish_date(self):
        self.assertEqual(app_module.day("2026-07-15 23:30:00"), "16 Jul 2026")
        self.assertEqual(app_module.day("2026-01-15 23:30:00"), "15 Jan 2026")


class TestPostExpiryUsesIrishTime(AppTestCase):

    def post_form(self, expires_on):
        return {"title": "Drummer wanted", "description": "Weekly rehearsals.",
                "county_id": str(self.county("Dublin")), "commitment": "Casual",
                "instrument_ids": [str(self.instrument("Drums"))], "expires_on": expires_on}

    def test_chosen_day_ends_at_midnight_irish_time(self):
        self.log_in_as_new_user()
        chosen = irish_time.today() + timedelta(days=10)
        self.client.post("/posts", data=self.post_form(chosen.isoformat()))
        post = db.list_open_posts()[0]
        self.assertEqual(post["expires_at"], irish_time.end_of_day_utc(chosen))

    def test_last_allowed_day_is_never_more_than_30_days(self):
        self.log_in_as_new_user()
        chosen = irish_time.today() + timedelta(days=30)
        page = self.client.post("/posts", data=self.post_form(chosen.isoformat()))
        self.assertEqual(page.status_code, 302)
        post = db.list_open_posts()[0]
        self.assertLessEqual(post["expires_at"], db.add_days(post["created_at"], 30))

    def test_today_is_refused(self):
        self.log_in_as_new_user()
        page = self.client.post("/posts", data=self.post_form(irish_time.today().isoformat()))
        self.assertIn(b"must be after today", page.data)


if __name__ == "__main__":
    unittest.main()
