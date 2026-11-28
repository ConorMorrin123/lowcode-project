-- bandfinder/schema/001_initial.sql
-- Built from bandfinder/docs/data-model.md. SQLite syntax.
-- Dates and times are stored as TEXT in the form YYYY-MM-DD HH:MM:SS.
-- Remember: every connection must run PRAGMA foreign_keys = ON (see db.py).

-- ---------------------------------------------------------------
-- Fixed dropdown lists
-- ---------------------------------------------------------------

CREATE TABLE county (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- primary key
    name TEXT NOT NULL UNIQUE                                      -- required, must never repeat
);

CREATE TABLE instrument (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- primary key
    name TEXT NOT NULL UNIQUE                                      -- required, must never repeat
);

CREATE TABLE genre (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- primary key
    name TEXT NOT NULL UNIQUE                                      -- required, must never repeat
);

-- ---------------------------------------------------------------
-- Users and their profiles
-- ---------------------------------------------------------------

CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- primary key
    username TEXT NOT NULL UNIQUE
        CHECK (length(username) BETWEEN 3 AND 30),                 -- required, unique, 3-30 characters
    email TEXT NOT NULL UNIQUE
        CHECK (email LIKE '%_@_%'),                                -- required, unique, must contain @
    password_hash TEXT NOT NULL,                                   -- required, stored hashed
    is_admin INTEGER NOT NULL DEFAULT 0
        CHECK (is_admin IN (0, 1)),                                -- 0 = member, 1 = admin
    confirmed_adult INTEGER NOT NULL
        CHECK (confirmed_adult = 1),                               -- must tick "I am 18 or over"
    display_name TEXT CHECK (length(display_name) <= 50),          -- optional
    photo_path TEXT,                                               -- optional, uploaded photo file name
    bio TEXT CHECK (length(bio) <= 500),                           -- optional
    age_range TEXT
        CHECK (age_range IN ('18-24', '25-34', '35-44', '45-54', '55+')), -- optional
    years_playing INTEGER
        CHECK (years_playing BETWEEN 0 AND 80),                    -- optional
    influences TEXT CHECK (length(influences) <= 500),             -- optional
    gear TEXT CHECK (length(gear) <= 500),                         -- optional
    county_id INTEGER
        REFERENCES county (id) ON DELETE RESTRICT,                 -- optional; a county in use can't be removed
    commitment TEXT
        CHECK (commitment IN ('Casual', 'Serious')),               -- optional
    project_type TEXT
        CHECK (project_type IN ('Original band', 'Covers band', 'Wedding / function band',
                                'Jam only', 'Session work')),      -- optional
    availability TEXT
        CHECK (availability IN ('Weeknights', 'Weekends',
                                'Weeknights and weekends', 'Flexible')), -- optional
    soundcloud_url TEXT CHECK (soundcloud_url LIKE 'https://%'),   -- optional link
    youtube_url TEXT CHECK (youtube_url LIKE 'https://%'),         -- optional link
    spotify_url TEXT CHECK (spotify_url LIKE 'https://%'),         -- optional link
    instagram_url TEXT CHECK (instagram_url LIKE 'https://%'),     -- optional link
    public_email TEXT CHECK (public_email LIKE '%_@_%'),           -- optional contact email shown on profile
    public_phone TEXT CHECK (length(public_phone) <= 20),          -- optional contact phone shown on profile
    created_at TEXT NOT NULL DEFAULT (datetime('now'))             -- required, set automatically
);

CREATE TABLE user_instrument (
    user_id INTEGER NOT NULL
        REFERENCES user (id) ON DELETE CASCADE,                    -- deleting the user deletes this row
    instrument_id INTEGER NOT NULL
        REFERENCES instrument (id) ON DELETE RESTRICT,             -- an instrument in use can't be removed
    skill_level TEXT NOT NULL
        CHECK (skill_level IN ('Beginner', 'Intermediate', 'Advanced', 'Pro')), -- skill on this instrument
    PRIMARY KEY (user_id, instrument_id)                           -- each instrument once per user
);

CREATE TABLE user_genre (
    user_id INTEGER NOT NULL
        REFERENCES user (id) ON DELETE CASCADE,                    -- deleting the user deletes this row
    genre_id INTEGER NOT NULL
        REFERENCES genre (id) ON DELETE RESTRICT,                  -- a genre in use can't be removed
    PRIMARY KEY (user_id, genre_id)                                -- each genre once per user
);

-- ---------------------------------------------------------------
-- The posting forum
-- ---------------------------------------------------------------

CREATE TABLE post (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- primary key
    user_id INTEGER
        REFERENCES user (id) ON DELETE SET NULL,                   -- author; emptied ("Deleted user") if the user is deleted
    title TEXT NOT NULL
        CHECK (length(title) BETWEEN 1 AND 100),                   -- required
    description TEXT NOT NULL
        CHECK (length(description) BETWEEN 1 AND 2000),            -- required
    county_id INTEGER NOT NULL
        REFERENCES county (id) ON DELETE RESTRICT,                 -- required; a county in use can't be removed
    commitment TEXT NOT NULL
        CHECK (commitment IN ('Casual', 'Serious')),               -- required
    created_at TEXT NOT NULL DEFAULT (datetime('now')),            -- required, set automatically
    expires_at TEXT NOT NULL,                                      -- required; the app sets 30 days by default
    CHECK (expires_at > created_at
           AND expires_at <= datetime(created_at, '+30 days'))     -- must be within 30 days of posting
);

CREATE TABLE post_instrument (
    post_id INTEGER NOT NULL
        REFERENCES post (id) ON DELETE CASCADE,                    -- deleting the post deletes this row
    instrument_id INTEGER NOT NULL
        REFERENCES instrument (id) ON DELETE RESTRICT,             -- an instrument in use can't be removed
    PRIMARY KEY (post_id, instrument_id)                           -- each instrument once per post
);

CREATE TABLE post_genre (
    post_id INTEGER NOT NULL
        REFERENCES post (id) ON DELETE CASCADE,                    -- deleting the post deletes this row
    genre_id INTEGER NOT NULL
        REFERENCES genre (id) ON DELETE RESTRICT,                  -- a genre in use can't be removed
    PRIMARY KEY (post_id, genre_id)                                -- each genre once per post
);

CREATE TABLE comment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- primary key
    post_id INTEGER NOT NULL
        REFERENCES post (id) ON DELETE CASCADE,                    -- deleting the post deletes its comments
    user_id INTEGER
        REFERENCES user (id) ON DELETE SET NULL,                   -- author; emptied ("Deleted user") if the user is deleted
    body TEXT NOT NULL
        CHECK (length(body) BETWEEN 1 AND 1000),                   -- required; kept even if an admin removes it
    created_at TEXT NOT NULL DEFAULT (datetime('now')),            -- required, set automatically
    removed_by_admin INTEGER NOT NULL DEFAULT 0
        CHECK (removed_by_admin IN (0, 1)),                        -- 1 = shown as "Removed by admin"
    removed_at TEXT,                                               -- when an admin removed it
    CHECK ((removed_by_admin = 0 AND removed_at IS NULL)
        OR (removed_by_admin = 1 AND removed_at IS NOT NULL))      -- removed_at only when removed
);

-- ---------------------------------------------------------------
-- Safety
-- ---------------------------------------------------------------

CREATE TABLE report (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- primary key
    reporter_id INTEGER
        REFERENCES user (id) ON DELETE SET NULL,                   -- who reported; emptied if that user is deleted
    reported_user_id INTEGER
        REFERENCES user (id) ON DELETE SET NULL,                   -- who was reported; emptied if that user is deleted
    reason TEXT NOT NULL
        CHECK (length(reason) BETWEEN 1 AND 1000),                 -- required
    status TEXT NOT NULL DEFAULT 'Open'
        CHECK (status IN ('Open', 'Resolved')),                    -- required
    created_at TEXT NOT NULL DEFAULT (datetime('now')),            -- required, set automatically
    CHECK (reporter_id <> reported_user_id)                        -- nobody can report themselves
);

-- ---------------------------------------------------------------
-- Fill in the dropdown lists
-- ---------------------------------------------------------------

INSERT INTO county (name) VALUES
    ('Antrim'), ('Armagh'), ('Carlow'), ('Cavan'), ('Clare'), ('Cork'), ('Derry'), ('Donegal'),
    ('Down'), ('Dublin'), ('Fermanagh'), ('Galway'), ('Kerry'), ('Kildare'), ('Kilkenny'), ('Laois'),
    ('Leitrim'), ('Limerick'), ('Longford'), ('Louth'), ('Mayo'), ('Meath'), ('Monaghan'), ('Offaly'),
    ('Roscommon'), ('Sligo'), ('Tipperary'), ('Tyrone'), ('Waterford'), ('Westmeath'), ('Wexford'), ('Wicklow');

INSERT INTO instrument (name) VALUES
    ('Lead guitar'), ('Rhythm guitar'), ('Bass'), ('Drums'), ('Vocals'), ('Backing vocals'),
    ('Keyboard / Piano'), ('Synth'), ('Violin'), ('Saxophone'), ('Trumpet'), ('DJ / Electronics'), ('Other');

INSERT INTO genre (name) VALUES
    ('Rock'), ('Indie'), ('Alternative'), ('Punk'), ('Metal'), ('Pop'), ('Folk'), ('Trad / Irish'),
    ('Blues'), ('Jazz'), ('Funk'), ('Soul / R&B'), ('Hip hop'), ('Electronic'), ('Country'),
    ('Reggae'), ('Covers / Mixed');
