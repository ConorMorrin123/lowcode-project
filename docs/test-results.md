# Database checks and test results

This file records what was checked about the Album Club database, what was found, and what was done about it.

- **Date:** 2026-11-16
- **Branch:** feature/data-model
- **Schema at the time:** `schema/001_initial.sql` and `schema/002_restrict_deletes.sql`

## 1. Data layer check (`tools/check_db.py`)

Command (run from the top project folder):

```bash
python tools/check_db.py app.db --src .
```

### First run: before `002_restrict_deletes.sql`

Summary: **Nothing to fix, 13 things to look at.**

| What it passed | |
|---|---|
| All 7 tables found (album, club, membership, proposal, review, user, vote) | ✓ |
| Every table has a primary key and NOT NULL on required fields | ✓ |
| No orphan rows (rows pointing at something that does not exist) | ✓ |
| No SQL built from glued-together strings (f-strings, `.format`, `%`, `+`) | ✓ |
| `PRAGMA foreign_keys = ON` is set in `albumclub/db.py` | ✓ |
| No Python lists used as in-memory storage | ✓ |

The 13 warnings and what was decided:

| Warning | Finding | What was done |
|---|---|---|
| club → album, membership, proposal, vote are CASCADE (4) | Already my decision: deleting a club deletes all its data, for privacy. | Reason already in `docs/data-model.md`. Kept. |
| user → membership is CASCADE (1) | Already my decision: a membership has no meaning without its user. | `docs/data-model.md` corrected so `membership.user_id` is required (it wrongly said "can be emptied"). Kept. |
| album → proposal is CASCADE (1) | **Not my decision.** It was chosen when the schema was generated. | Changed to **RESTRICT** (see section 2). |
| proposal → vote is CASCADE (1) | **Not my decision.** | Changed to **RESTRICT** (see section 2). |
| album → review is CASCADE (1) | **Not my decision.** | Kept as **CASCADE** after testing (see section 2). |
| album has no UNIQUE rule (1) | A club should not hold the same album twice. Today only the app checks this (title + artist, ignoring capital letters). | Open. Could be added with a new migration using a UNIQUE index. |
| proposal has no UNIQUE rule (1) | Nothing here must never repeat: an album can be proposed again after it is rejected. | Left as it is, on purpose. |
| album, user, vote have no CHECK rule (3) | `album.release_year` could have a range (the app already checks 1900 to next year). user and vote have no fixed list of values. | Open for album. Left as it is for user and vote, on purpose. |

### Second run: after `002_restrict_deletes.sql`

Summary: **Nothing to fix, 11 things to look at.** The two warnings for album → proposal and proposal → vote are gone because they are now RESTRICT. The checker still lists every CASCADE as a warning. Each one now has its reason in `docs/data-model.md`.

## 2. Finding: RESTRICT on reviews would break deleting a club

I wanted RESTRICT on all three undecided delete rules, to protect the club's history. Before changing the schema, each rule was tested on a small in-memory copy of the tables, to see whether deleting a whole club still worked.

| Rule set to RESTRICT | Can a whole club still be deleted? |
|---|---|
| album → proposal | ✅ Yes |
| proposal → vote | ✅ Yes |
| album → review | ❌ **No, it is blocked** |

**Why:** a review is linked only to an album and has no `club_id` of its own. Deleting a club deletes its albums (CASCADE). With RESTRICT, the database refuses to delete an album that still has reviews, so the whole club delete fails. Proposals and votes do not have this problem: they have their own `club_id`, so the club CASCADE removes them directly.

**Decision:** RESTRICT for album → proposal and proposal → vote. CASCADE stays for album → review. This keeps both my club CASCADE rule and the protection for proposals and votes. Reasons are in `docs/data-model.md`.

**How it was applied:** a new migration, `schema/002_restrict_deletes.sql`. SQLite cannot change a delete rule in place, so it rebuilds the proposal and vote tables: it renames the old tables, creates the new ones, copies every row with the same ids, and drops the old ones. `001_initial.sql` was not edited.

**How it was checked (on copies, never the real `app.db`):**

- Copy of `app.db`: same number of rows in every table before and after, and `PRAGMA foreign_key_check` found no broken links.
- Fresh database with demo data:
  - deleting an album with proposals was refused,
  - deleting a proposal with votes was refused,
  - deleting a whole club worked and removed everything in it.
- The app's main pages still worked: logging in, proposing, voting, reviewing, and closing voting.

## 3. Constraint tests (`tests/test_constraints.py`)

Command (run from the top project folder):

```bash
python3 -m unittest discover -s tests -v
```

Each test builds a brand-new temporary database by running the files in `schema/` in number order (with `tools/migrate.py`), and deletes it afterwards. The real `app.db` is never opened: its size and date were the same before and after the run.

**Result: 34 tests, all passed.** No changes to the app, `db.py` or the schema were needed.

| Group | Bad data tried (all rejected) | Tests |
|---|---|---|
| UNIQUE | Duplicate username; duplicate email; duplicate club name; duplicate invite code; a second membership in the same club; a second vote in the same club in the same week; a second review of the same album by the same user | 7 |
| CHECK | Privacy setting `secret`; changeover day `Funday`; role `owner`; membership status `banned`; proposal status `won`; rating 6; rating 0 | 7 |
| NOT NULL | User with no email; club with no description; album with no title; proposal with no week_start; review with no text | 5 |
| Foreign key | Membership for a missing club or a missing user; album for a missing club; proposal for a missing album; vote for a missing proposal; review for a missing album. Plus a test that `db.get_connection()` really turns foreign keys on | 7 |

Delete rules (one test each, all passed):

| Rule | What the test proves |
|---|---|
| club → everything: CASCADE | Deleting a club leaves no memberships, albums, proposals, votes or reviews behind. |
| user → membership: CASCADE | Deleting a user deletes their memberships. |
| user → proposal, vote, review: SET NULL | Deleting a user keeps their proposals, votes and reviews, but `proposed_by`, `approved_by` and `user_id` become empty. |
| album → proposal: RESTRICT | Deleting an album that has a proposal is refused, and both rows are still there. |
| proposal → vote: RESTRICT | Deleting a proposal that has a vote is refused, and both rows are still there. |
| album → review: CASCADE | Deleting an album with no proposals also deletes its reviews. |

Other tests:

| Test | Result |
|---|---|
| Persistence: save a user, close the connection, open a new one and read it back | Passed: the user was still there. |
| Not found: ask for id 999 (user, club, album, proposal, review, membership), an unknown invite code and an unknown username | Passed: each returned `None`, not an error. |

**Not run:** the tests were not run under pytest because pytest is not installed. The file uses plain `unittest`, which pytest can also run (`python3 -m pip install pytest`, then `python3 -m pytest tests -v`).

## 4. Still open

- Add a UNIQUE rule to album (same club, title and artist), as a new migration.
- Decide whether `album.release_year` should have a CHECK range in the database, not just in the app.
- Apply `002_restrict_deletes.sql` to the real database: `python3 tools/migrate.py app.db`.
- `albumclub/albumclub.db` (the old database file) is still tracked by Git, even though `.gitignore` lists `*.db`. Remove it from Git with `git rm --cached albumclub/albumclub.db`.
