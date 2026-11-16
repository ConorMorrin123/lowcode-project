"""Tests that prove the database rejects bad data and follows the delete rules.

Every test gets its own brand-new temporary database, built by running the
files in schema/ in number order (using tools/migrate.py, the same tool used
for the real app). The real app.db is never opened.

Run from the top project folder:
    python -m unittest discover -s tests -v
    python -m pytest tests -v        (if pytest is installed)
"""
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT, "albumclub"))  # so we can import db.py
sys.path.insert(0, os.path.join(PROJECT, "tools"))      # so we can import migrate.py

import db       # noqa: E402  (albumclub/db.py)
import migrate  # noqa: E402  (tools/migrate.py)

WEEK = "2026-11-16"


class DatabaseTestCase(unittest.TestCase):
    """Creates a fresh temporary database before each test and deletes it after."""

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.db_path = os.path.join(self.folder, "test.db")
        # Safety net: never let a test run against the real database.
        self.assertNotEqual(os.path.basename(self.db_path), "app.db")
        migrate.migrate(self.db_path, os.path.join(PROJECT, "schema"), quiet=True)

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

    def make_user(self, username="aoife"):
        return db.create_user(username, username + "@example.com", "hashed-password")

    def make_club(self, admin_id, name="Friday Club", code="CODE-1"):
        return db.create_club(name, "A test club", code, "open", "Monday", admin_id)

    def make_album(self, club_id, title="Rumours"):
        return db.create_album(club_id, title, "Fleetwood Mac", "Rock", 1977)

    def make_everything(self):
        """One user, club, album, proposal, vote and review that all link up."""
        user = self.make_user()
        club = self.make_club(user)
        album = self.make_album(club)
        proposal = db.create_proposal(club, album, user, WEEK)
        vote = db.create_vote(club, proposal, user, WEEK)
        review = db.create_review(album, user, 5, "Great")
        return user, club, album, proposal, vote, review

    def count(self, table):
        conn = db.get_connection()
        try:
            # Table names cannot be ? placeholders, so only fixed names are allowed here.
            queries = {
                "membership": "SELECT COUNT(*) FROM membership",
                "album": "SELECT COUNT(*) FROM album",
                "proposal": "SELECT COUNT(*) FROM proposal",
                "vote": "SELECT COUNT(*) FROM vote",
                "review": "SELECT COUNT(*) FROM review",
            }
            return conn.execute(queries[table]).fetchone()[0]
        finally:
            conn.close()


# --------------------------------------------------------------------- UNIQUE

class UniqueTests(DatabaseTestCase):

    def test_duplicate_username_is_rejected(self):
        db.create_user("aoife", "aoife@example.com", "hash")
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_user("aoife", "other@example.com", "hash")

    def test_duplicate_email_is_rejected(self):
        db.create_user("aoife", "same@example.com", "hash")
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_user("ciaran", "same@example.com", "hash")

    def test_duplicate_club_name_is_rejected(self):
        user = self.make_user()
        self.make_club(user, name="Friday Club", code="CODE-1")
        with self.assertRaises(sqlite3.IntegrityError):
            self.make_club(user, name="Friday Club", code="CODE-2")

    def test_duplicate_invite_code_is_rejected(self):
        user = self.make_user()
        self.make_club(user, name="Club A", code="SAME")
        with self.assertRaises(sqlite3.IntegrityError):
            self.make_club(user, name="Club B", code="SAME")

    def test_second_membership_in_same_club_is_rejected(self):
        user = self.make_user()
        club = self.make_club(user)  # this already makes the admin membership
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_membership(user, club, "member", "active")

    def test_second_vote_in_same_week_is_rejected(self):
        user, club, album, proposal, _, _ = self.make_everything()
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_vote(club, proposal, user, WEEK)

    def test_second_review_of_same_album_is_rejected(self):
        user, _, album, _, _, _ = self.make_everything()
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_review(album, user, 3, "Changed my mind")


# ---------------------------------------------------------------------- CHECK

class CheckTests(DatabaseTestCase):

    def test_bad_privacy_setting_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_club("Club", "desc", "CODE", "secret", "Monday", user)

    def test_bad_changeover_day_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_club("Club", "desc", "CODE", "open", "Funday", user)

    def test_bad_membership_role_is_rejected(self):
        admin = self.make_user("aoife")
        club = self.make_club(admin)
        other = self.make_user("ciaran")
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_membership(other, club, "owner", "active")

    def test_bad_membership_status_is_rejected(self):
        admin = self.make_user("aoife")
        club = self.make_club(admin)
        other = self.make_user("ciaran")
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_membership(other, club, "member", "banned")

    def test_bad_proposal_status_is_rejected(self):
        user, _, _, proposal, _, _ = self.make_everything()
        with self.assertRaises(sqlite3.IntegrityError):
            db.update_proposal_status(proposal, "won", user)

    def test_rating_above_5_is_rejected(self):
        user = self.make_user()
        album = self.make_album(self.make_club(user))
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_review(album, user, 6, "Too good")

    def test_rating_below_1_is_rejected(self):
        user = self.make_user()
        album = self.make_album(self.make_club(user))
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_review(album, user, 0, "Too bad")


# ------------------------------------------------------------------- NOT NULL

class NotNullTests(DatabaseTestCase):

    def test_user_without_email_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_user("aoife", None, "hash")

    def test_club_without_description_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_club("Club", None, "CODE", "open", "Monday", user)

    def test_album_without_title_is_rejected(self):
        club = self.make_club(self.make_user())
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_album(club, None, "Artist", "Rock")

    def test_proposal_without_week_start_is_rejected(self):
        user = self.make_user()
        club = self.make_club(user)
        album = self.make_album(club)
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_proposal(club, album, user, None)

    def test_review_without_text_is_rejected(self):
        user = self.make_user()
        album = self.make_album(self.make_club(user))
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_review(album, user, 4, None)


# ---------------------------------------------------------------- FOREIGN KEY
# All of these go through db.py, so they also prove get_connection()
# really turns foreign keys on (SQLite would accept them otherwise).

class ForeignKeyTests(DatabaseTestCase):

    def test_get_connection_turns_foreign_keys_on(self):
        conn = db.get_connection()
        try:
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        finally:
            conn.close()

    def test_membership_for_missing_club_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_membership(user, 999, "member", "active")

    def test_membership_for_missing_user_is_rejected(self):
        club = self.make_club(self.make_user())
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_membership(999, club, "member", "active")

    def test_album_for_missing_club_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_album(999, "Rumours", "Fleetwood Mac", "Rock")

    def test_proposal_for_missing_album_is_rejected(self):
        user = self.make_user()
        club = self.make_club(user)
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_proposal(club, 999, user, WEEK)

    def test_vote_for_missing_proposal_is_rejected(self):
        user = self.make_user()
        club = self.make_club(user)
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_vote(club, 999, user, WEEK)

    def test_review_for_missing_album_is_rejected(self):
        user = self.make_user()
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_review(999, user, 5, "Great")


# --------------------------------------------------------------- DELETE RULES

class DeleteRuleTests(DatabaseTestCase):

    def test_deleting_club_deletes_everything_in_it(self):
        """CASCADE: club -> memberships, albums, proposals, votes, reviews."""
        _, club, _, _, _, _ = self.make_everything()
        db.delete_club(club)
        self.assertIsNone(db.get_club(club))
        for table in ("membership", "album", "proposal", "vote", "review"):
            self.assertEqual(self.count(table), 0, table + " rows were left behind")

    def test_deleting_user_deletes_their_memberships(self):
        """CASCADE: user -> memberships."""
        user, club, _, _, _, _ = self.make_everything()
        db.delete_user(user)
        self.assertIsNone(db.get_membership(club, user))
        self.assertEqual(self.count("membership"), 0)

    def test_deleting_user_keeps_their_activity_but_empties_the_link(self):
        """SET NULL: user -> proposals (proposed_by, approved_by), votes, reviews."""
        user, club, album, proposal, vote, review = self.make_everything()
        db.update_proposal_status(proposal, "approved", user)
        db.delete_user(user)

        kept_proposal = db.get_proposal(proposal)
        self.assertIsNotNone(kept_proposal)
        self.assertIsNone(kept_proposal["proposed_by"])
        self.assertIsNone(kept_proposal["approved_by"])

        kept_review = db.get_review(review)
        self.assertIsNotNone(kept_review)
        self.assertIsNone(kept_review["user_id"])

        kept_votes = db.list_votes(proposal)
        self.assertEqual(len(kept_votes), 1)
        self.assertIsNone(kept_votes[0]["user_id"])

    def test_deleting_album_with_proposals_is_blocked(self):
        """RESTRICT: album -> proposals."""
        _, _, album, proposal, _, _ = self.make_everything()
        with self.assertRaises(sqlite3.IntegrityError):
            db.delete_album(album)
        self.assertIsNotNone(db.get_album(album))
        self.assertIsNotNone(db.get_proposal(proposal))

    def test_deleting_proposal_with_votes_is_blocked(self):
        """RESTRICT: proposal -> votes."""
        _, _, _, proposal, _, _ = self.make_everything()
        with self.assertRaises(sqlite3.IntegrityError):
            db.delete_proposal(proposal)
        self.assertIsNotNone(db.get_proposal(proposal))
        self.assertEqual(len(db.list_votes(proposal)), 1)

    def test_deleting_album_without_proposals_deletes_its_reviews(self):
        """CASCADE: album -> reviews (only possible once nothing else blocks it)."""
        user = self.make_user()
        album = self.make_album(self.make_club(user))
        review = db.create_review(album, user, 4, "Nice")
        db.delete_album(album)
        self.assertIsNone(db.get_review(review))


# ---------------------------------------------------------------- PERSISTENCE

class PersistenceTests(DatabaseTestCase):

    def test_data_survives_closing_and_reopening_the_file(self):
        conn = db.get_connection()
        cur = conn.execute(
            "INSERT INTO user (username, email, password_hash) VALUES (?, ?, ?)",
            ("aoife", "aoife@example.com", "hash"))
        user_id = cur.lastrowid
        conn.commit()
        conn.close()

        reopened = db.get_connection()  # a brand-new connection to the same file
        try:
            row = reopened.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
        finally:
            reopened.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["username"], "aoife")


# ------------------------------------------------------------------ NOT FOUND

class NotFoundTests(DatabaseTestCase):

    def test_missing_ids_return_none(self):
        self.assertIsNone(db.get_user(999))
        self.assertIsNone(db.get_club(999))
        self.assertIsNone(db.get_album(999))
        self.assertIsNone(db.get_proposal(999))
        self.assertIsNone(db.get_review(999))
        self.assertIsNone(db.get_membership(999, 999))
        self.assertIsNone(db.get_club_by_invite_code("NO-SUCH-CODE"))
        self.assertIsNone(db.get_user_by_username("nobody"))


if __name__ == "__main__":
    unittest.main()
