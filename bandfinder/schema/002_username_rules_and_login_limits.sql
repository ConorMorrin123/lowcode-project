-- bandfinder/schema/002_username_rules_and_login_limits.sql
-- Fixes from the Week 3 code review (docs2/week03-review.md).
-- SQLite can't add a CHECK rule to an existing table, so the username
-- character rule is enforced with triggers instead. They work the same way:
-- the database refuses the row.

-- Review fix: usernames that differ only in capitals ("Aoife" / "aoife")
-- must count as the same username.
-- (If two such usernames already exist, this file fails and nothing changes.
--  Rename one of them, then run the migration again.)
CREATE UNIQUE INDEX user_username_nocase ON user (username COLLATE NOCASE);

-- Review fix: usernames may only use letters, numbers, _ and -.
-- Anything else (for example "/" or a space) broke the profile page link.
CREATE TRIGGER user_username_characters_insert
BEFORE INSERT ON user
WHEN NEW.username GLOB '*[^A-Za-z0-9_-]*'
BEGIN
    SELECT RAISE(ABORT, 'username may only use letters, numbers, _ and -');
END;

CREATE TRIGGER user_username_characters_update
BEFORE UPDATE OF username ON user
WHEN NEW.username GLOB '*[^A-Za-z0-9_-]*'
BEGIN
    SELECT RAISE(ABORT, 'username may only use letters, numbers, _ and -');
END;

-- Review fix: limit wrong login attempts.
-- One row per failed attempt. Stored by email (not linked to a user), so it
-- also counts attempts on emails that don't exist, and nothing needs deleting
-- when a user is deleted.
CREATE TABLE login_attempt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- primary key
    email TEXT NOT NULL CHECK (length(email) BETWEEN 1 AND 320),   -- the email that was typed in
    attempted_at TEXT NOT NULL DEFAULT (datetime('now'))           -- when (UTC)
);

CREATE INDEX login_attempt_email_time ON login_attempt (email, attempted_at);
