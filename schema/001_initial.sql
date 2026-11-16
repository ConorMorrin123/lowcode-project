-- schema/001_initial.sql
-- Built from docs/data-model.md. SQLite syntax.
-- Dates are stored as TEXT in YYYY-MM-DD form.
-- Remember: every connection must run PRAGMA foreign_keys = ON (see db.py).

CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- primary key
    username TEXT NOT NULL UNIQUE,                                 -- required, must never repeat
    email TEXT NOT NULL UNIQUE,                                    -- required, must never repeat
    password_hash TEXT NOT NULL,                                   -- required, stored scrambled
    profile_picture TEXT NOT NULL DEFAULT '/static/default_profile.png', -- required, one fixed stock picture by default
    music_taste TEXT                                               -- optional
);

CREATE TABLE club (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- primary key
    name TEXT NOT NULL UNIQUE,                                     -- required, must never repeat
    description TEXT NOT NULL,                                     -- required
    invite_code TEXT NOT NULL UNIQUE,                              -- required, must never repeat
    privacy_setting TEXT NOT NULL
        CHECK (privacy_setting IN ('open', 'invite_only')),        -- required, only these two values
    changeover_day TEXT NOT NULL
        CHECK (changeover_day IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday',
                                  'Friday', 'Saturday', 'Sunday')) -- required, a day of the week
);

CREATE TABLE membership (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- primary key
    user_id INTEGER NOT NULL
        REFERENCES user (id) ON DELETE CASCADE,                    -- required link to user; deleting the user deletes the membership
    club_id INTEGER NOT NULL
        REFERENCES club (id) ON DELETE CASCADE,                    -- required link to club; deleting the club deletes it
    role TEXT NOT NULL
        CHECK (role IN ('admin', 'member')),                       -- required, only these two values
    status TEXT NOT NULL
        CHECK (status IN ('pending', 'active', 'left')),           -- required, only these three values
    joined_at TEXT NOT NULL,                                       -- required date (YYYY-MM-DD)
    UNIQUE (user_id, club_id)                                      -- one membership per person per club
);

CREATE TABLE album (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- primary key
    club_id INTEGER NOT NULL
        REFERENCES club (id) ON DELETE CASCADE,                    -- required link to club; deleting the club deletes it
    title TEXT NOT NULL,                                           -- required
    artist TEXT NOT NULL,                                          -- required
    genre TEXT NOT NULL,                                           -- required
    release_year INTEGER,                                          -- optional
    cover_art_url TEXT,                                            -- optional
    listening_url TEXT                                             -- optional
);

CREATE TABLE proposal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- primary key
    club_id INTEGER NOT NULL
        REFERENCES club (id) ON DELETE CASCADE,                    -- required link to club; deleting the club deletes it
    album_id INTEGER NOT NULL
        REFERENCES album (id) ON DELETE CASCADE,                   -- required link to album; deleting the album deletes it
    proposed_by INTEGER
        REFERENCES user (id) ON DELETE SET NULL,                   -- who proposed it; emptied if the user is deleted
    approved_by INTEGER
        REFERENCES user (id) ON DELETE SET NULL,                   -- admin who decided; emptied if the user is deleted
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'winner')), -- required, only these four values
    week_start TEXT NOT NULL,                                      -- required date (YYYY-MM-DD)
    created_at TEXT NOT NULL                                       -- required date (YYYY-MM-DD)
);

CREATE TABLE vote (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- primary key
    club_id INTEGER NOT NULL
        REFERENCES club (id) ON DELETE CASCADE,                    -- required link to club; deleting the club deletes it
    proposal_id INTEGER NOT NULL
        REFERENCES proposal (id) ON DELETE CASCADE,                -- required link to proposal; deleting the proposal deletes it
    user_id INTEGER
        REFERENCES user (id) ON DELETE SET NULL,                   -- who voted; emptied if the user is deleted
    week_start TEXT NOT NULL,                                      -- required date (YYYY-MM-DD)
    created_at TEXT NOT NULL,                                      -- required date (YYYY-MM-DD)
    UNIQUE (user_id, club_id, week_start)                          -- one vote per member per club per week
);

CREATE TABLE review (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- primary key
    album_id INTEGER NOT NULL
        REFERENCES album (id) ON DELETE CASCADE,                   -- required link to album; deleting the album deletes it
    user_id INTEGER
        REFERENCES user (id) ON DELETE SET NULL,                   -- who wrote it; emptied if the user is deleted
    rating INTEGER NOT NULL
        CHECK (rating BETWEEN 1 AND 5),                            -- required, 1 to 5 stars
    review_text TEXT NOT NULL,                                     -- required
    created_at TEXT NOT NULL,                                      -- required date (YYYY-MM-DD)
    updated_at TEXT NOT NULL,                                      -- required date (YYYY-MM-DD)
    UNIQUE (album_id, user_id)                                     -- one review per member per album
);
