"""Tests that prove the Band Finder database rejects bad data and follows the delete rules.

Every test gets its own brand-new temporary database, built by running the
files in bandfinder/schema/ in number order (using tools/migrate.py, the same
tool used for the real app). The real bandfinder/app.db is never opened.

Run from the lowcode-project folder:
    python -m unittest discover -s bandfinder/tests -v
    python -m pytest bandfinder/tests -v        (if pytest is installed)
"""
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

BANDFINDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.path.dirname(BANDFINDER)
sys.path.insert(0, BANDFINDER)                      # so we can import bandfinder/db.py
sys.path.insert(0, os.path.join(PROJECT, "tools"))  # so we can import tools/migrate.py

import db       # noqa: E402  (bandfinder/db.py)
import migrate  # noqa: E402  (tools/migrate.py)


class DatabaseTestCase(unittest.TestCase):
    """Creates a fresh temporary database before each test and deletes it after."""

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.db_path = os.path.join(self.folder, "test.db")
        # Safety net: never let a test run against the real database.
        self.assertNotEqual(os.path.basename(self.db_path), "app.db")
        migrate.migrate(self.db_path, os.path.join(BANDFINDER, "schema"), quiet=True)

        # db.get_connection() reads DATABASE_PATH, so point it at the temp file.
        self.old_path = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = self.db_path

    def tearDown(self):
        if self.old_path is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = self.old_path
        shutil.rmtree(self.folder, ignore_errors=True)

    # ---- small helpers that make valid rows, so each test only adds the bad part

    def lookup(self, table_query, name):
        """Find a dropdown id by name, e.g. self.county('Dublin')."""
        conn = db.get_connection()
        try:
            return conn.execute(table_query, (name,)).fetchone()["id"]
        finally:
            conn.close()

    def county(self, name):
        return self.lookup("SELECT id FROM county WHERE name = ?", name)

    def instrument(self, name):
        return self.lookup("SELECT id FROM instrument WHERE name = ?", name)

    def genre(self, name):
        return self.lookup("SELECT id FROM genre WHERE name = ?", name)

    def make_user(self, username="aoife"):
        return db.create_user(username, username + "@example.com", "hashed-password", 1)

    def make_post(self, user_id, county="Dublin", instruments=("Drums",), genres=("Rock",),
                  title="Drummer wanted"):
        return db.create_post(
            user_id, title, "Indie rock band looking for a drummer.",
            self.county(county), "Serious",
            [self.instrument(name) for name in instruments],
            [self.genre(name) for name in genres])

    def run_sql(self, sql, params=()):
        """Run one statement directly, the way a buggy route might."""
        conn = db.get_connection()
        try:
            conn.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    def count(self, table):
        conn = db.get_connection()
        try:
            # Table names cannot be ? placeholders, so only fixed names are allowed here.
            queries = {
                "user_instrument": "SELECT COUNT(*) FROM user_instrument",
                "user_genre": "SELECT COUNT(*) FROM user_genre",
                "post": "SELECT COUNT(*) FROM post",
                "post_instrument": "SELECT COUNT(*) FROM post_instrument",
                "post_genre": "SELECT COUNT(*) FROM post_genre",
                "comment": "SELECT COUNT(*) FROM comment",
                "report": "SELECT COUNT(*) FROM report",
            }
            return conn.execute(queries[table]).fetchone()[0]
        finally:
            conn.close()


class TestSetup(DatabaseTestCase):

    def test_foreign_keys_are_switched_on(self):
        conn = db.get_connection()
        try:
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        finally:
            conn.close()

    def test_dropdown_lists_are_filled_in(self):
        self.assertEqual(len(db.list_counties()), 32)
        self.assertEqual(len(db.list_instruments()), 13)
        self.assertEqual(len(db.list_genres()), 17)


class TestDuplicates(DatabaseTestCase):

    def test_duplicate_username_is_rejected(self):
        self.make_user("aoife")
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_user("aoife", "other@example.com", "hash", 1)

    def test_duplicate_email_is_rejected(self):
        self.make_user("aoife")
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_user("someone", "aoife@example.com", "hash", 1)

    def test_same_instrument_twice_for_one_user_is_rejected(self):
        user = self.make_user()
        drums = self.instrument("Drums")
        with self.assertRaises(sqlite3.IntegrityError):
            db.set_user_instruments(user, [(drums, "Pro"), (drums, "Beginner")])
        self.assertEqual(self.count("user_instrument"), 0)  # nothing half-saved

    def test_same_genre_twice_on_a_post_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            self.make_post(user, genres=("Rock", "Rock"))
        self.assertEqual(self.count("post"), 0)  # the post was not saved either

    def test_duplicate_dropdown_item_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_sql("INSERT INTO county (name) VALUES (?)", ("Dublin",))


class TestCheckRules(DatabaseTestCase):

    def test_must_confirm_18_or_over(self):
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_user("young", "young@example.com", "hash", 0)

    def test_username_too_short_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_user("ab", "ab@example.com", "hash", 1)

    def test_email_without_at_sign_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_user("aoife", "not-an-email", "hash", 1)

    def test_is_admin_must_be_0_or_1(self):
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_user("aoife", "aoife@example.com", "hash", 1, is_admin=2)

    def test_unknown_skill_level_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.set_user_instruments(user, [(self.instrument("Bass"), "Godlike")])

    def test_unknown_profile_dropdown_values_are_rejected(self):
        user = self.make_user()
        for bad in ({"age_range": "16-17"}, {"commitment": "Sometimes"},
                    {"project_type": "Boy band"}, {"availability": "Never"}):
            with self.subTest(bad=bad):
                with self.assertRaises(sqlite3.IntegrityError):
                    db.update_profile(user, **bad)

    def test_years_playing_out_of_range_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.update_profile(user, years_playing=-1)
        with self.assertRaises(sqlite3.IntegrityError):
            db.update_profile(user, years_playing=81)

    def test_link_must_start_with_https(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.update_profile(user, spotify_url="http://open.spotify.com/artist/1")

    def test_bio_over_500_characters_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.update_profile(user, bio="x" * 501)

    def test_post_expiring_after_30_days_is_rejected(self):
        user = self.make_user()
        too_late = db.add_days(db.now(), 31)
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_post(user, "Title", "Description", self.county("Dublin"), "Casual",
                           [], [], expires_at=too_late)

    def test_post_expiring_before_it_was_made_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_post(user, "Title", "Description", self.county("Dublin"), "Casual",
                           [], [], expires_at="2000-01-01 00:00:00")

    def test_post_with_earlier_expiry_is_allowed(self):
        user = self.make_user()
        post = db.create_post(user, "Title", "Description", self.county("Dublin"), "Casual",
                              [], [], expires_at=db.add_days(db.now(), 7))
        self.assertIsNotNone(db.get_post(post))

    def test_post_gets_30_day_expiry_by_default(self):
        user = self.make_user()
        post = db.get_post(self.make_post(user))
        self.assertEqual(post["expires_at"], db.add_days(post["created_at"], 30))

    def test_unknown_commitment_on_post_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_post(user, "Title", "Description", self.county("Dublin"), "Maybe", [], [])

    def test_empty_post_title_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_post(user, "", "Description", self.county("Dublin"), "Casual", [], [])

    def test_cannot_report_yourself(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_report(user, user, "Reporting myself")

    def test_unknown_report_status_is_rejected(self):
        a, b = self.make_user("aoife"), self.make_user("brian")
        report = db.create_report(a, b, "Spam")
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_sql("UPDATE report SET status = 'Ignored' WHERE id = ?", (report,))

    def test_removed_comment_needs_a_removal_date(self):
        user = self.make_user()
        comment = db.create_comment(self.make_post(user), user, "Hello")
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_sql("UPDATE comment SET removed_by_admin = 1 WHERE id = ?", (comment,))


class TestUsernameRules(DatabaseTestCase):
    """Week 3 review fixes, added in 002_username_rules_and_login_limits.sql."""

    def test_username_with_a_slash_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_user("a/b", "ab@example.com", "hash", 1)

    def test_username_with_a_space_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_user("a b", "ab@example.com", "hash", 1)

    def test_changing_a_username_to_bad_characters_is_rejected(self):
        user = self.make_user("aoife")
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_sql("UPDATE user SET username = 'aoife!' WHERE id = ?", (user,))

    def test_same_username_with_different_capitals_is_rejected(self):
        self.make_user("Aoife")
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_user("aoife", "other@example.com", "hash", 1)

    def test_letters_numbers_underscore_and_dash_are_allowed(self):
        self.assertIsNotNone(db.create_user("Dub_Drummer-99", "d@example.com", "hash", 1))


class TestLoginAttempts(DatabaseTestCase):

    def test_attempt_without_email_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_sql("INSERT INTO login_attempt (email) VALUES (NULL)")

    def test_locked_after_five_wrong_attempts(self):
        for _ in range(4):
            db.record_failed_login("aoife@example.com")
        self.assertFalse(db.is_login_locked("aoife@example.com"))
        db.record_failed_login("aoife@example.com")
        self.assertTrue(db.is_login_locked("aoife@example.com"))
        self.assertFalse(db.is_login_locked("someone-else@example.com"))

    def test_old_attempts_do_not_count(self):
        for _ in range(5):
            self.run_sql("INSERT INTO login_attempt (email, attempted_at) VALUES (?, ?)",
                         ("aoife@example.com", db.minutes_ago(16)))
        self.assertFalse(db.is_login_locked("aoife@example.com"))

    def test_clearing_attempts_unlocks(self):
        for _ in range(5):
            db.record_failed_login("aoife@example.com")
        db.clear_failed_logins("aoife@example.com")
        self.assertFalse(db.is_login_locked("aoife@example.com"))


class TestMissingRequiredFields(DatabaseTestCase):

    def test_user_without_password_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_user("aoife", "aoife@example.com", None, 1)

    def test_post_without_county_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_post(user, "Title", "Description", None, "Casual", [], [])

    def test_post_without_description_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_post(user, "Title", None, self.county("Dublin"), "Casual", [], [])

    def test_comment_without_body_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_comment(self.make_post(user), user, None)

    def test_report_without_reason_is_rejected(self):
        a, b = self.make_user("aoife"), self.make_user("brian")
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_report(a, b, None)


class TestLinksToThingsThatDoNotExist(DatabaseTestCase):

    def test_post_in_a_county_that_does_not_exist_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_post(user, "Title", "Description", 999, "Casual", [], [])

    def test_post_by_a_user_that_does_not_exist_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_post(999, "Title", "Description", self.county("Dublin"), "Casual", [], [])

    def test_instrument_that_does_not_exist_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.set_user_instruments(user, [(999, "Pro")])

    def test_comment_on_a_post_that_does_not_exist_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_comment(999, user, "Hello")

    def test_report_about_a_user_that_does_not_exist_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_report(user, 999, "Spam")


class TestDeleteRules(DatabaseTestCase):

    def test_deleting_a_user_keeps_their_posts_as_deleted_user(self):      # SET NULL
        user = self.make_user()
        post = self.make_post(user)
        db.delete_user(user)
        kept = db.get_post(post)
        self.assertIsNotNone(kept)
        self.assertIsNone(kept["user_id"])
        self.assertIsNone(kept["username"])   # the page shows "Deleted user"

    def test_deleting_a_user_keeps_their_comments_as_deleted_user(self):   # SET NULL
        author, commenter = self.make_user("aoife"), self.make_user("brian")
        post = self.make_post(author)
        comment = db.create_comment(post, commenter, "I play drums!")
        db.delete_user(commenter)
        kept = db.get_comment(comment)
        self.assertIsNotNone(kept)
        self.assertIsNone(kept["user_id"])

    def test_deleting_a_user_keeps_reports_as_deleted_user(self):          # SET NULL
        a, b = self.make_user("aoife"), self.make_user("brian")
        report = db.create_report(a, b, "Spam")
        db.delete_user(a)
        db.delete_user(b)
        rows = db.list_open_reports()
        self.assertEqual([r["id"] for r in rows], [report])
        self.assertIsNone(rows[0]["reporter_id"])
        self.assertIsNone(rows[0]["reported_user_id"])

    def test_deleting_a_user_deletes_their_instruments_and_genres(self):   # CASCADE
        user = self.make_user()
        db.set_user_instruments(user, [(self.instrument("Bass"), "Advanced")])
        db.set_user_genres(user, [self.genre("Rock"), self.genre("Indie")])
        db.delete_user(user)
        self.assertEqual(self.count("user_instrument"), 0)
        self.assertEqual(self.count("user_genre"), 0)

    def test_deleting_a_post_deletes_its_comments_and_tags(self):          # CASCADE
        user = self.make_user()
        post = self.make_post(user, instruments=("Drums", "Bass"), genres=("Rock", "Indie"))
        db.create_comment(post, user, "Bump")
        db.delete_post(post)
        self.assertEqual(self.count("comment"), 0)
        self.assertEqual(self.count("post_instrument"), 0)
        self.assertEqual(self.count("post_genre"), 0)

    def test_county_in_use_cannot_be_deleted(self):                         # RESTRICT
        self.make_post(self.make_user(), county="Cork")
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_sql("DELETE FROM county WHERE id = ?", (self.county("Cork"),))

    def test_instrument_in_use_cannot_be_deleted(self):                     # RESTRICT
        user = self.make_user()
        db.set_user_instruments(user, [(self.instrument("Violin"), "Pro")])
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_sql("DELETE FROM instrument WHERE id = ?", (self.instrument("Violin"),))

    def test_genre_in_use_cannot_be_deleted(self):                          # RESTRICT
        self.make_post(self.make_user(), genres=("Jazz",))
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_sql("DELETE FROM genre WHERE id = ?", (self.genre("Jazz"),))

    def test_unused_dropdown_item_can_be_deleted(self):
        self.run_sql("DELETE FROM genre WHERE id = ?", (self.genre("Reggae"),))
        self.assertEqual(len(db.list_genres()), 16)


class TestAdminRemovesComment(DatabaseTestCase):

    def test_removed_comment_keeps_its_author_and_text(self):
        user = self.make_user()
        comment = db.create_comment(self.make_post(user), user, "Rude words")
        db.remove_comment_by_admin(comment)
        row = db.get_comment(comment)
        self.assertEqual(row["removed_by_admin"], 1)
        self.assertIsNotNone(row["removed_at"])
        self.assertEqual(row["user_id"], user)
        self.assertEqual(row["body"], "Rude words")   # kept for admins; hidden on the page


class TestFiltersAndSuggestions(DatabaseTestCase):

    def test_expired_posts_are_hidden(self):
        user = self.make_user()
        live = self.make_post(user)
        self.run_sql(
            """INSERT INTO post (user_id, title, description, county_id, commitment,
                                 created_at, expires_at)
               VALUES (?, 'Old', 'Old post', ?, 'Casual', '2026-01-01 00:00:00', '2026-01-31 00:00:00')""",
            (user, self.county("Dublin")))
        self.assertEqual([p["id"] for p in db.list_open_posts()], [live])

    def test_filters_by_instrument_genre_and_county(self):
        user = self.make_user()
        dublin_drums = self.make_post(user, county="Dublin", instruments=("Drums",), genres=("Rock",))
        cork_bass = self.make_post(user, county="Cork", instruments=("Bass",), genres=("Jazz",))
        ids = lambda rows: [p["id"] for p in rows]  # noqa: E731
        self.assertEqual(ids(db.list_open_posts(instrument_id=self.instrument("Bass"))), [cork_bass])
        self.assertEqual(ids(db.list_open_posts(genre_id=self.genre("Rock"))), [dublin_drums])
        self.assertEqual(ids(db.list_open_posts(county_id=self.county("Cork"))), [cork_bass])
        self.assertEqual(ids(db.list_open_posts(county_id=self.county("Cork"),
                                                genre_id=self.genre("Rock"))), [])

    def test_filters_by_skill_level_of_the_poster(self):
        pro, beginner = self.make_user("aoife"), self.make_user("brian")
        db.set_user_instruments(pro, [(self.instrument("Lead guitar"), "Pro")])
        db.set_user_instruments(beginner, [(self.instrument("Bass"), "Beginner")])
        pro_post = self.make_post(pro)
        self.make_post(beginner)
        self.assertEqual([p["id"] for p in db.list_open_posts(skill_level="Pro")], [pro_post])

    def test_suggestions_rank_best_match_first_and_skip_own_posts(self):
        me, other = self.make_user("aoife"), self.make_user("brian")
        db.update_profile(me, county_id=self.county("Dublin"))
        db.set_user_instruments(me, [(self.instrument("Drums"), "Advanced")])
        db.set_user_genres(me, [self.genre("Rock")])
        best = self.make_post(other, county="Dublin", instruments=("Drums",), genres=("Rock",))  # 3+2+1
        okay = self.make_post(other, county="Cork", instruments=("Drums",), genres=("Jazz",))    # 3
        self.make_post(other, county="Cork", instruments=("Bass",), genres=("Jazz",))            # 0: left out
        self.make_post(me, county="Dublin", instruments=("Drums",), genres=("Rock",))            # mine: left out
        self.assertEqual([p["id"] for p in db.suggested_posts(me)], [best, okay])
        self.assertEqual(db.suggested_posts(me)[0]["score"], 6)


class TestDataSurvivesRestart(DatabaseTestCase):

    def test_data_is_still_there_after_closing_and_reopening(self):
        user = self.make_user("aoife")
        post = self.make_post(user)
        # Every db function closes its connection, so the file has been closed.
        # Open a completely new connection to the same file and look again.
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute("SELECT title FROM post WHERE id = ?", (post,)).fetchone()
            name = conn.execute("SELECT username FROM user WHERE id = ?", (user,)).fetchone()
        finally:
            conn.close()
        self.assertEqual(row[0], "Drummer wanted")
        self.assertEqual(name[0], "aoife")


if __name__ == "__main__":
    unittest.main()
