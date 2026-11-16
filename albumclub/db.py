"""All database access for Album Club lives in this file.

Rules (see AGENTS.md):
  * Every connection comes from get_connection(), which turns foreign keys on.
  * Every value goes into SQL through a ? placeholder. No f-strings, no +.
  * This file never creates or changes tables. The tables come from the
    numbered files in schema/, applied with:  python tools/migrate.py app.db
  * A "get" function returns None when nothing is found.
  * Functions that write data let sqlite3.IntegrityError escape, so the
    route can show the user a friendly message.

Each function opens its own connection and always closes it again
(that is what the try / finally blocks do).
"""
import os
import sqlite3
from datetime import date, timedelta

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ---------------------------------------------------------------- basics

def get_connection():
    """Open the database file named in DATABASE_PATH (default app.db)."""
    path = os.environ.get("DATABASE_PATH", "app.db")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row          # rows behave like dictionaries
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite ignores foreign keys without this
    return conn


def today():
    """Today's date as text, e.g. '2026-11-16'."""
    return date.today().isoformat()


def current_week_start(changeover_day, on_date=None):
    """The most recent changeover day (today counts), as 'YYYY-MM-DD'.
    Example: if a club changes over on Monday, every day from Monday to
    Sunday belongs to the week that started on that Monday."""
    on_date = on_date or date.today()
    days_back = (on_date.weekday() - DAYS.index(changeover_day)) % 7
    return (on_date - timedelta(days=days_back)).isoformat()


# ------------------------------------------------------------------ user

def create_user(username, email, password_hash, music_taste=None):
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO user (username, email, password_hash, music_taste) VALUES (?, ?, ?, ?)",
            (username, email, password_hash, music_taste))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_user(user_id):
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
    finally:
        conn.close()


def get_user_by_username(username):
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM user WHERE username = ?", (username,)).fetchone()
    finally:
        conn.close()


def list_users():
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM user ORDER BY username").fetchall()
    finally:
        conn.close()


def update_user(user_id, email, music_taste):
    conn = get_connection()
    try:
        conn.execute("UPDATE user SET email = ?, music_taste = ? WHERE id = ?",
                     (email, music_taste, user_id))
        conn.commit()
    finally:
        conn.close()


def delete_user(user_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM user WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------------------------ club

def create_club(name, description, invite_code, privacy_setting, changeover_day, admin_user_id):
    """Create a club and make admin_user_id its first (admin) member.
    Both rows are saved together, or neither is."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO club (name, description, invite_code, privacy_setting, changeover_day)
               VALUES (?, ?, ?, ?, ?)""",
            (name, description, invite_code, privacy_setting, changeover_day))
        club_id = cur.lastrowid
        conn.execute(
            """INSERT INTO membership (user_id, club_id, role, status, joined_at)
               VALUES (?, ?, 'admin', 'active', ?)""",
            (admin_user_id, club_id, today()))
        conn.commit()
        return club_id
    finally:
        conn.close()  # closing without commit throws away a half-finished change


def get_club(club_id):
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM club WHERE id = ?", (club_id,)).fetchone()
    finally:
        conn.close()


def get_club_by_invite_code(invite_code):
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM club WHERE invite_code = ?", (invite_code,)).fetchone()
    finally:
        conn.close()


def list_clubs_for_user(user_id):
    """Clubs where this user is an active member, with their role."""
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT c.id, c.name, c.description, m.role
               FROM membership m JOIN club c ON c.id = m.club_id
               WHERE m.user_id = ? AND m.status = 'active'
               ORDER BY c.name""",
            (user_id,)).fetchall()
    finally:
        conn.close()


def update_club(club_id, name, description, privacy_setting, changeover_day):
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE club SET name = ?, description = ?, privacy_setting = ?, changeover_day = ?
               WHERE id = ?""",
            (name, description, privacy_setting, changeover_day, club_id))
        conn.commit()
    finally:
        conn.close()


def delete_club(club_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM club WHERE id = ?", (club_id,))
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------------------ membership

def create_membership(user_id, club_id, role, status):
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO membership (user_id, club_id, role, status, joined_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, club_id, role, status, today()))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_membership(club_id, user_id):
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM membership WHERE club_id = ? AND user_id = ?",
            (club_id, user_id)).fetchone()
    finally:
        conn.close()


def list_members(club_id):
    """Active members of a club, admins first."""
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT m.id, m.role, m.joined_at, u.username
               FROM membership m JOIN user u ON u.id = m.user_id
               WHERE m.club_id = ? AND m.status = 'active'
               ORDER BY m.role, u.username""",
            (club_id,)).fetchall()
    finally:
        conn.close()


def update_membership(membership_id, role, status):
    conn = get_connection()
    try:
        conn.execute("UPDATE membership SET role = ?, status = ? WHERE id = ?",
                     (role, status, membership_id))
        conn.commit()
    finally:
        conn.close()


def delete_membership(membership_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM membership WHERE id = ?", (membership_id,))
        conn.commit()
    finally:
        conn.close()


# ----------------------------------------------------------------- album

def create_album(club_id, title, artist, genre, release_year=None,
                 cover_art_url=None, listening_url=None):
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO album (club_id, title, artist, genre, release_year, cover_art_url, listening_url)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (club_id, title, artist, genre, release_year, cover_art_url, listening_url))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_album(album_id):
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM album WHERE id = ?", (album_id,)).fetchone()
    finally:
        conn.close()


def find_album(club_id, title, artist):
    """This club's copy of an album, matched on title and artist (ignoring case)."""
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT * FROM album
               WHERE club_id = ? AND lower(title) = lower(?) AND lower(artist) = lower(?)""",
            (club_id, title, artist)).fetchone()
    finally:
        conn.close()


def list_albums(club_id):
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM album WHERE club_id = ? ORDER BY artist, title", (club_id,)).fetchall()
    finally:
        conn.close()


def update_album(album_id, title, artist, genre, release_year, cover_art_url, listening_url):
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE album SET title = ?, artist = ?, genre = ?, release_year = ?,
                                cover_art_url = ?, listening_url = ?
               WHERE id = ?""",
            (title, artist, genre, release_year, cover_art_url, listening_url, album_id))
        conn.commit()
    finally:
        conn.close()


def delete_album(album_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM album WHERE id = ?", (album_id,))
        conn.commit()
    finally:
        conn.close()


def album_is_reviewable(album_id):
    """True once one of this album's proposals has been approved (or won)."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT 1 FROM proposal
               WHERE album_id = ? AND status IN ('approved', 'winner')""",
            (album_id,)).fetchone()
        return row is not None
    finally:
        conn.close()


def album_has_open_proposal(album_id):
    """True if the album is already pending, approved or a past winner."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT 1 FROM proposal
               WHERE album_id = ? AND status IN ('pending', 'approved', 'winner')""",
            (album_id,)).fetchone()
        return row is not None
    finally:
        conn.close()


# -------------------------------------------------------------- proposal

def create_proposal(club_id, album_id, proposed_by, week_start):
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO proposal (club_id, album_id, proposed_by, status, week_start, created_at)
               VALUES (?, ?, ?, 'pending', ?, ?)""",
            (club_id, album_id, proposed_by, week_start, today()))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def propose_album(club_id, user_id, week_start, album_id, title, artist, genre,
                  release_year, cover_art_url, listening_url):
    """Create the proposal. If album_id is None, first create the club's
    copy of the album. Both are saved together, or neither is."""
    conn = get_connection()
    try:
        if album_id is None:
            cur = conn.execute(
                """INSERT INTO album (club_id, title, artist, genre, release_year,
                                      cover_art_url, listening_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (club_id, title, artist, genre, release_year, cover_art_url, listening_url))
            album_id = cur.lastrowid
        cur = conn.execute(
            """INSERT INTO proposal (club_id, album_id, proposed_by, status, week_start, created_at)
               VALUES (?, ?, ?, 'pending', ?, ?)""",
            (club_id, album_id, user_id, week_start, today()))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_proposal(proposal_id):
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT p.id, p.club_id, p.album_id, p.proposed_by, p.approved_by, p.status,
                   p.week_start, p.created_at,
                   a.title, a.artist, a.genre, a.release_year, a.cover_art_url, a.listening_url,
                   u.username AS proposer_name,
                   (SELECT AVG(r.rating) FROM review r WHERE r.album_id = p.album_id) AS avg_rating,
                   (SELECT COUNT(*) FROM review r WHERE r.album_id = p.album_id) AS review_count
            FROM proposal p
            JOIN album a ON a.id = p.album_id
            LEFT JOIN user u ON u.id = p.proposed_by
            WHERE p.id = ?""",
            (proposal_id,)).fetchone()
    finally:
        conn.close()


def list_proposals(club_id, status):
    """A club's proposals with one status, oldest first."""
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT p.id, p.club_id, p.album_id, p.proposed_by, p.approved_by, p.status,
                   p.week_start, p.created_at,
                   a.title, a.artist, a.genre, a.release_year, a.cover_art_url, a.listening_url,
                   u.username AS proposer_name,
                   (SELECT AVG(r.rating) FROM review r WHERE r.album_id = p.album_id) AS avg_rating,
                   (SELECT COUNT(*) FROM review r WHERE r.album_id = p.album_id) AS review_count
            FROM proposal p
            JOIN album a ON a.id = p.album_id
            LEFT JOIN user u ON u.id = p.proposed_by
            WHERE p.club_id = ? AND p.status = ?
            ORDER BY p.id""",
            (club_id, status)).fetchall()
    finally:
        conn.close()


def list_approved_with_votes(club_id, week_start):
    """Approved proposals with the number of votes each has this week."""
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT p.id, p.club_id, p.album_id, p.proposed_by, p.approved_by, p.status,
                   p.week_start, p.created_at,
                   a.title, a.artist, a.genre, a.release_year, a.cover_art_url, a.listening_url,
                   u.username AS proposer_name,
                   (SELECT AVG(r.rating) FROM review r WHERE r.album_id = p.album_id) AS avg_rating,
                   (SELECT COUNT(*) FROM review r WHERE r.album_id = p.album_id) AS review_count,
                   (SELECT COUNT(*) FROM vote v
                    WHERE v.proposal_id = p.id AND v.week_start = ?) AS votes
            FROM proposal p
            JOIN album a ON a.id = p.album_id
            LEFT JOIN user u ON u.id = p.proposed_by
            WHERE p.club_id = ? AND p.status = 'approved'
            ORDER BY p.id""",
            (week_start, club_id)).fetchall()
    finally:
        conn.close()


def list_winners(club_id):
    """Past and current albums of the week, newest first."""
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT p.id, p.club_id, p.album_id, p.proposed_by, p.approved_by, p.status,
                   p.week_start, p.created_at,
                   a.title, a.artist, a.genre, a.release_year, a.cover_art_url, a.listening_url,
                   u.username AS proposer_name,
                   (SELECT AVG(r.rating) FROM review r WHERE r.album_id = p.album_id) AS avg_rating,
                   (SELECT COUNT(*) FROM review r WHERE r.album_id = p.album_id) AS review_count
            FROM proposal p
            JOIN album a ON a.id = p.album_id
            LEFT JOIN user u ON u.id = p.proposed_by
            WHERE p.club_id = ? AND p.status = 'winner'
            ORDER BY p.week_start DESC, p.id DESC""",
            (club_id,)).fetchall()
    finally:
        conn.close()


def update_proposal_status(proposal_id, status, approved_by):
    conn = get_connection()
    try:
        conn.execute("UPDATE proposal SET status = ?, approved_by = ? WHERE id = ?",
                     (status, approved_by, proposal_id))
        conn.commit()
    finally:
        conn.close()


def delete_proposal(proposal_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM proposal WHERE id = ?", (proposal_id,))
        conn.commit()
    finally:
        conn.close()


def winner_exists_for_week(club_id, week_start):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM proposal WHERE club_id = ? AND status = 'winner' AND week_start = ?",
            (club_id, week_start)).fetchone()
        return row is not None
    finally:
        conn.close()


def pick_winner(club_id, week_start):
    """Make the approved proposal with the most votes this week the winner.
    Ties go to the oldest proposal. Returns the winning proposal id, or None
    if nobody has voted. The other approved proposals stay approved and
    carry over to next week's vote."""
    conn = get_connection()
    try:
        top = conn.execute(
            """SELECT p.id, COUNT(v.id) AS n
               FROM proposal p
               LEFT JOIN vote v ON v.proposal_id = p.id AND v.week_start = ?
               WHERE p.club_id = ? AND p.status = 'approved'
               GROUP BY p.id
               ORDER BY n DESC, p.id ASC
               LIMIT 1""",
            (week_start, club_id)).fetchone()
        if top is None or top["n"] == 0:
            return None
        conn.execute("UPDATE proposal SET status = 'winner', week_start = ? WHERE id = ?",
                     (week_start, top["id"]))
        conn.commit()
        return top["id"]
    finally:
        conn.close()


# ------------------------------------------------------------------ vote

def create_vote(club_id, proposal_id, user_id, week_start):
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO vote (club_id, proposal_id, user_id, week_start, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (club_id, proposal_id, user_id, week_start, today()))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_vote(club_id, user_id, week_start):
    """This user's vote in this club for this week, or None."""
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM vote WHERE club_id = ? AND user_id = ? AND week_start = ?",
            (club_id, user_id, week_start)).fetchone()
    finally:
        conn.close()


def list_votes(proposal_id):
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM vote WHERE proposal_id = ? ORDER BY id", (proposal_id,)).fetchall()
    finally:
        conn.close()


def update_vote(vote_id, proposal_id):
    """Move an existing vote to a different proposal."""
    conn = get_connection()
    try:
        conn.execute("UPDATE vote SET proposal_id = ?, created_at = ? WHERE id = ?",
                     (proposal_id, today(), vote_id))
        conn.commit()
    finally:
        conn.close()


def delete_vote(vote_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM vote WHERE id = ?", (vote_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- review

def create_review(album_id, user_id, rating, review_text):
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO review (album_id, user_id, rating, review_text, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (album_id, user_id, rating, review_text, today(), today()))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_review(review_id):
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM review WHERE id = ?", (review_id,)).fetchone()
    finally:
        conn.close()


def get_user_review(album_id, user_id):
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM review WHERE album_id = ? AND user_id = ?",
            (album_id, user_id)).fetchone()
    finally:
        conn.close()


def list_reviews(album_id):
    """Reviews of an album with the reviewer's username (None if their account was deleted)."""
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT r.*, u.username
               FROM review r LEFT JOIN user u ON u.id = r.user_id
               WHERE r.album_id = ? ORDER BY r.id""",
            (album_id,)).fetchall()
    finally:
        conn.close()


def update_review(review_id, rating, review_text):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE review SET rating = ?, review_text = ?, updated_at = ? WHERE id = ?",
            (rating, review_text, today(), review_id))
        conn.commit()
    finally:
        conn.close()


def delete_review(review_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM review WHERE id = ?", (review_id,))
        conn.commit()
    finally:
        conn.close()
