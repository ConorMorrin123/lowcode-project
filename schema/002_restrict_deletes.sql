-- schema/002_restrict_deletes.sql
-- Changes two delete rules from CASCADE to RESTRICT (decided by the student,
-- reasons in docs/data-model.md):
--   * album -> proposal : an album that has proposals cannot be deleted
--   * proposal -> vote  : a proposal that has votes cannot be deleted
-- album -> review stays CASCADE, so deleting a whole club still works.
--
-- SQLite cannot change a foreign key in place, so the two tables are rebuilt:
-- move the old tables aside, create the new ones, copy every row across,
-- then drop the old ones. tools/migrate.py runs this whole file in one
-- transaction, so if anything fails nothing is changed.

-- 1. Move the old tables aside. Renaming proposal also updates vote_old so it
--    points at proposal_old, which keeps the votes safe while we work.
ALTER TABLE vote RENAME TO vote_old;
ALTER TABLE proposal RENAME TO proposal_old;

-- 2. New proposal table: identical to 001_initial.sql except album_id is RESTRICT.
CREATE TABLE proposal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- primary key
    club_id INTEGER NOT NULL
        REFERENCES club (id) ON DELETE CASCADE,                    -- deleting the club deletes it
    album_id INTEGER NOT NULL
        REFERENCES album (id) ON DELETE RESTRICT,                  -- an album with proposals cannot be deleted
    proposed_by INTEGER
        REFERENCES user (id) ON DELETE SET NULL,                   -- emptied if the user is deleted
    approved_by INTEGER
        REFERENCES user (id) ON DELETE SET NULL,                   -- emptied if the user is deleted
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'winner')),
    week_start TEXT NOT NULL,                                      -- YYYY-MM-DD
    created_at TEXT NOT NULL                                       -- YYYY-MM-DD
);

-- 3. New vote table: identical to 001_initial.sql except proposal_id is RESTRICT.
CREATE TABLE vote (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- primary key
    club_id INTEGER NOT NULL
        REFERENCES club (id) ON DELETE CASCADE,                    -- deleting the club deletes it
    proposal_id INTEGER NOT NULL
        REFERENCES proposal (id) ON DELETE RESTRICT,               -- a proposal with votes cannot be deleted
    user_id INTEGER
        REFERENCES user (id) ON DELETE SET NULL,                   -- emptied if the user is deleted
    week_start TEXT NOT NULL,                                      -- YYYY-MM-DD
    created_at TEXT NOT NULL,                                      -- YYYY-MM-DD
    UNIQUE (user_id, club_id, week_start)                          -- one vote per member per club per week
);

-- 4. Copy every row across, keeping the same ids.
INSERT INTO proposal (id, club_id, album_id, proposed_by, approved_by, status, week_start, created_at)
    SELECT id, club_id, album_id, proposed_by, approved_by, status, week_start, created_at
    FROM proposal_old;

INSERT INTO vote (id, club_id, proposal_id, user_id, week_start, created_at)
    SELECT id, club_id, proposal_id, user_id, week_start, created_at
    FROM vote_old;

-- 5. Remove the old tables (votes first, because they point at proposals).
DROP TABLE vote_old;
DROP TABLE proposal_old;
