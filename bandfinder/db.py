"""All database access for Band Finder lives in this file.

Rules (see AGENTS.md):
  * Every connection comes from get_connection(), which turns foreign keys on.
  * Every value goes into SQL through a ? placeholder. No f-strings, no +.
  * This file never creates or changes tables. The tables come from the
    numbered files in bandfinder/schema/, applied with (from lowcode-project/):
        python tools/migrate.py bandfinder/app.db --schema bandfinder/schema
  * A "get" function returns None when nothing is found.
  * Functions that write data let sqlite3.IntegrityError escape, so the
    route can show the user a friendly message.

Each function opens its own connection and always closes it again
(that is what the try / finally blocks do).
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))

POST_LIFETIME_DAYS = 30   # posts expire after 30 days (the default and the maximum)
SUGGESTION_COUNT = 3      # how many posts "Suggested for you" shows


# ---------------------------------------------------------------- basics

def get_connection():
    """Open the database file named in DATABASE_PATH (default bandfinder/app.db)."""
    path = os.environ.get("DATABASE_PATH", os.path.join(HERE, "app.db"))
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row            # rows behave like dictionaries
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite ignores foreign keys without this
    return conn


def now():
    """The current time (UTC) as text, e.g. '2026-11-28 17:30:00'.
    Same format as SQLite's datetime('now'), so the two can be compared."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def add_days(timestamp, days):
    """Add a number of days to a 'YYYY-MM-DD HH:MM:SS' timestamp."""
    moment = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    return (moment + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


# -------------------------------------------------------- dropdown lists

def list_counties():
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM county ORDER BY name").fetchall()
    finally:
        conn.close()


def list_instruments():
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM instrument ORDER BY id").fetchall()
    finally:
        conn.close()


def list_genres():
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM genre ORDER BY name").fetchall()
    finally:
        conn.close()


# ------------------------------------------------------------------ user

def create_user(username, email, password_hash, confirmed_adult, is_admin=0):
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO user (username, email, password_hash, confirmed_adult, is_admin)
               VALUES (?, ?, ?, ?, ?)""",
            (username, email, password_hash, confirmed_adult, is_admin))
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


def get_user_by_email(email):
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM user WHERE email = ?", (email,)).fetchone()
    finally:
        conn.close()


def list_users():
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM user ORDER BY username").fetchall()
    finally:
        conn.close()


def update_profile(user_id, display_name=None, photo_path=None, bio=None, age_range=None,
                   years_playing=None, influences=None, gear=None, county_id=None,
                   commitment=None, project_type=None, availability=None,
                   soundcloud_url=None, youtube_url=None, spotify_url=None,
                   instagram_url=None, public_email=None, public_phone=None):
    """Save every profile field at once. A field left as None is emptied."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE user SET
                   display_name = ?, photo_path = ?, bio = ?, age_range = ?,
                   years_playing = ?, influences = ?, gear = ?, county_id = ?,
                   commitment = ?, project_type = ?, availability = ?,
                   soundcloud_url = ?, youtube_url = ?, spotify_url = ?, instagram_url = ?,
                   public_email = ?, public_phone = ?
               WHERE id = ?""",
            (display_name, photo_path, bio, age_range, years_playing, influences, gear,
             county_id, commitment, project_type, availability, soundcloud_url,
             youtube_url, spotify_url, instagram_url, public_email, public_phone, user_id))
        conn.commit()
    finally:
        conn.close()


def make_admin(user_id):
    conn = get_connection()
    try:
        conn.execute("UPDATE user SET is_admin = 1 WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def delete_user(user_id):
    """Delete an account. Their posts, comments and reports stay, shown as
    "Deleted user" (SET NULL). Their instruments and genres go (CASCADE)."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM user WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def set_user_instruments(user_id, instruments):
    """Replace a user's instruments. `instruments` is a list of
    (instrument_id, skill_level) pairs. All saved together, or none are."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM user_instrument WHERE user_id = ?", (user_id,))
        for instrument_id, skill_level in instruments:
            conn.execute(
                "INSERT INTO user_instrument (user_id, instrument_id, skill_level) VALUES (?, ?, ?)",
                (user_id, instrument_id, skill_level))
        conn.commit()
    finally:
        conn.close()  # closing without commit throws away a half-finished change


def list_user_instruments(user_id):
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT i.id, i.name, ui.skill_level
               FROM user_instrument ui JOIN instrument i ON i.id = ui.instrument_id
               WHERE ui.user_id = ? ORDER BY i.id""",
            (user_id,)).fetchall()
    finally:
        conn.close()


def set_user_genres(user_id, genre_ids):
    """Replace a user's genres with the list of genre ids given."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM user_genre WHERE user_id = ?", (user_id,))
        for genre_id in genre_ids:
            conn.execute("INSERT INTO user_genre (user_id, genre_id) VALUES (?, ?)",
                         (user_id, genre_id))
        conn.commit()
    finally:
        conn.close()


def list_user_genres(user_id):
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT g.id, g.name
               FROM user_genre ug JOIN genre g ON g.id = ug.genre_id
               WHERE ug.user_id = ? ORDER BY g.name""",
            (user_id,)).fetchall()
    finally:
        conn.close()


# ------------------------------------------------------------------ post

def create_post(user_id, title, description, county_id, commitment,
                instrument_ids, genre_ids, expires_at=None):
    """Create a post with its wanted instruments and genres.
    If expires_at is not given it is set to 30 days from now.
    The post and its tags are saved together, or none are."""
    created_at = now()
    if expires_at is None:
        expires_at = add_days(created_at, POST_LIFETIME_DAYS)
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO post (user_id, title, description, county_id, commitment,
                                 created_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, title, description, county_id, commitment, created_at, expires_at))
        post_id = cur.lastrowid
        for instrument_id in instrument_ids:
            conn.execute("INSERT INTO post_instrument (post_id, instrument_id) VALUES (?, ?)",
                         (post_id, instrument_id))
        for genre_id in genre_ids:
            conn.execute("INSERT INTO post_genre (post_id, genre_id) VALUES (?, ?)",
                         (post_id, genre_id))
        conn.commit()
        return post_id
    finally:
        conn.close()


def get_post(post_id):
    """One post with its author's username (None if the author was deleted)
    and its county name."""
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT p.*, u.username, c.name AS county_name
               FROM post p
               LEFT JOIN user u ON u.id = p.user_id
               JOIN county c ON c.id = p.county_id
               WHERE p.id = ?""",
            (post_id,)).fetchone()
    finally:
        conn.close()


def list_post_instruments(post_id):
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT i.id, i.name
               FROM post_instrument pi JOIN instrument i ON i.id = pi.instrument_id
               WHERE pi.post_id = ? ORDER BY i.id""",
            (post_id,)).fetchall()
    finally:
        conn.close()


def list_post_genres(post_id):
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT g.id, g.name
               FROM post_genre pg JOIN genre g ON g.id = pg.genre_id
               WHERE pg.post_id = ? ORDER BY g.name""",
            (post_id,)).fetchall()
    finally:
        conn.close()


def list_open_posts(instrument_id=None, genre_id=None, county_id=None,
                    skill_level=None, commitment=None):
    """Posts that have not expired, newest first.
    Each filter left as None is ignored. The query never changes shape:
    "? IS NULL OR ..." simply switches a filter off when its value is None.
    skill_level matches posts whose author plays any instrument at that level."""
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT p.*, u.username, c.name AS county_name
               FROM post p
               LEFT JOIN user u ON u.id = p.user_id
               JOIN county c ON c.id = p.county_id
               WHERE p.expires_at > ?
                 AND (? IS NULL OR p.county_id = ?)
                 AND (? IS NULL OR p.commitment = ?)
                 AND (? IS NULL OR EXISTS (SELECT 1 FROM post_instrument pi
                                           WHERE pi.post_id = p.id AND pi.instrument_id = ?))
                 AND (? IS NULL OR EXISTS (SELECT 1 FROM post_genre pg
                                           WHERE pg.post_id = p.id AND pg.genre_id = ?))
                 AND (? IS NULL OR EXISTS (SELECT 1 FROM user_instrument ui
                                           WHERE ui.user_id = p.user_id AND ui.skill_level = ?))
               ORDER BY p.created_at DESC, p.id DESC""",
            (now(),
             county_id, county_id,
             commitment, commitment,
             instrument_id, instrument_id,
             genre_id, genre_id,
             skill_level, skill_level)).fetchall()
    finally:
        conn.close()


def suggested_posts(user_id):
    """"Suggested for you": open posts by other people, scored for this user.
      +3 if the post wants an instrument the user plays
      +2 if the post is in the user's county
      +1 for each genre the post shares with the user
    Posts scoring 0 are left out. Best 3 first."""
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT * FROM (
                   SELECT p.*, u.username, c.name AS county_name,
                          3 * EXISTS (SELECT 1 FROM post_instrument pi
                                      JOIN user_instrument ui ON ui.instrument_id = pi.instrument_id
                                      WHERE pi.post_id = p.id AND ui.user_id = ?)
                        + 2 * IFNULL(p.county_id = (SELECT county_id FROM user WHERE id = ?), 0)
                        + (SELECT COUNT(*) FROM post_genre pg
                           JOIN user_genre ug ON ug.genre_id = pg.genre_id
                           WHERE pg.post_id = p.id AND ug.user_id = ?) AS score
                   FROM post p
                   LEFT JOIN user u ON u.id = p.user_id
                   JOIN county c ON c.id = p.county_id
                   WHERE p.expires_at > ?
                     AND (p.user_id IS NULL OR p.user_id <> ?)
               )
               WHERE score > 0
               ORDER BY score DESC, created_at DESC
               LIMIT ?""",
            (user_id, user_id, user_id, now(), user_id, SUGGESTION_COUNT)).fetchall()
    finally:
        conn.close()


def delete_post(post_id):
    """Delete a post. Its comments and tags go with it (CASCADE)."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM post WHERE id = ?", (post_id,))
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------- comment

def create_comment(post_id, user_id, body):
    conn = get_connection()
    try:
        cur = conn.execute("INSERT INTO comment (post_id, user_id, body) VALUES (?, ?, ?)",
                           (post_id, user_id, body))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_comment(comment_id):
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM comment WHERE id = ?", (comment_id,)).fetchone()
    finally:
        conn.close()


def list_comments(post_id):
    """Comments on a post, oldest first, with the author's username
    (None if their account was deleted). Pages must show "Removed by admin"
    instead of the body when removed_by_admin is 1."""
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT cm.*, u.username
               FROM comment cm LEFT JOIN user u ON u.id = cm.user_id
               WHERE cm.post_id = ? ORDER BY cm.created_at, cm.id""",
            (post_id,)).fetchall()
    finally:
        conn.close()


def remove_comment_by_admin(comment_id):
    """Hide a comment from users. The row and its text stay in the database."""
    conn = get_connection()
    try:
        conn.execute("UPDATE comment SET removed_by_admin = 1, removed_at = ? WHERE id = ?",
                     (now(), comment_id))
        conn.commit()
    finally:
        conn.close()


def delete_comment(comment_id):
    """Used when the author deletes their own comment."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM comment WHERE id = ?", (comment_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- report

def create_report(reporter_id, reported_user_id, reason):
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO report (reporter_id, reported_user_id, reason) VALUES (?, ?, ?)",
            (reporter_id, reported_user_id, reason))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_open_reports():
    """Open reports with both usernames (None means "Deleted user")."""
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT r.*, a.username AS reporter_username, b.username AS reported_username
               FROM report r
               LEFT JOIN user a ON a.id = r.reporter_id
               LEFT JOIN user b ON b.id = r.reported_user_id
               WHERE r.status = 'Open' ORDER BY r.created_at, r.id""").fetchall()
    finally:
        conn.close()


def resolve_report(report_id):
    conn = get_connection()
    try:
        conn.execute("UPDATE report SET status = 'Resolved' WHERE id = ?", (report_id,))
        conn.commit()
    finally:
        conn.close()
