CREATE TABLE IF NOT EXISTS User (
    UserID  INTEGER PRIMARY KEY AUTOINCREMENT,
    Name    TEXT NOT NULL CHECK (length(Name) <= 200),
    Email   TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS Club (
    ClubID    INTEGER PRIMARY KEY AUTOINCREMENT,
    Name      TEXT NOT NULL CHECK (length(Name) <= 200),
    JoinCode  TEXT NOT NULL UNIQUE CHECK (length(JoinCode) <= 100)
);

CREATE TABLE IF NOT EXISTS Membership (
    MembershipID  INTEGER PRIMARY KEY AUTOINCREMENT,
    ClubID        INTEGER NOT NULL REFERENCES Club(ClubID),
    UserID        INTEGER NOT NULL REFERENCES User(UserID),
    Role          TEXT NOT NULL DEFAULT 'member' CHECK (Role IN ('admin', 'member')),
    JoinedAt      TEXT NOT NULL,
    UNIQUE (ClubID, UserID)
);

CREATE TABLE IF NOT EXISTS Album (
    AlbumID  INTEGER PRIMARY KEY AUTOINCREMENT,
    Title    TEXT NOT NULL COLLATE NOCASE,
    Artist   TEXT NOT NULL COLLATE NOCASE,
    Year     INTEGER NOT NULL,
    Genre    TEXT NOT NULL,
    UNIQUE (Title, Artist, Year)
);

CREATE TABLE IF NOT EXISTS Proposal (
    ProposalID  INTEGER PRIMARY KEY AUTOINCREMENT,
    ClubID      INTEGER NOT NULL REFERENCES Club(ClubID),
    AlbumID     INTEGER NOT NULL REFERENCES Album(AlbumID),
    ProposedBy  INTEGER NOT NULL REFERENCES User(UserID),
    Pitch       TEXT CHECK (Pitch IS NULL OR length(Pitch) <= 200),
    Status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (Status IN ('pending', 'approved', 'rejected', 'won', 'archived')),
    WonAt       TEXT
);

CREATE TABLE IF NOT EXISTS Vote (
    VoteID      INTEGER PRIMARY KEY AUTOINCREMENT,
    ProposalID  INTEGER NOT NULL REFERENCES Proposal(ProposalID),
    UserID      INTEGER NOT NULL REFERENCES User(UserID),
    ClubID      INTEGER NOT NULL REFERENCES Club(ClubID),
    CastAt      TEXT NOT NULL,
    UNIQUE (ProposalID, UserID)
);

CREATE TABLE IF NOT EXISTS Review (
    ReviewID    INTEGER PRIMARY KEY AUTOINCREMENT,
    ProposalID  INTEGER NOT NULL REFERENCES Proposal(ProposalID),
    UserID      INTEGER NOT NULL REFERENCES User(UserID),
    ClubID      INTEGER NOT NULL REFERENCES Club(ClubID),
    Rating      INTEGER NOT NULL CHECK (Rating BETWEEN 1 AND 5),
    Comment     TEXT,
    UNIQUE (ProposalID, UserID)
);