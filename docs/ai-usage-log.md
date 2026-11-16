# AI-usage log: [YOUR APP NAME]

This log is a graded part of CA2. It feeds the AI Fluency declaration (Delegation, Description, Discernment, Diligence). Add an entry every time AI does something meaningful for your project, including the times it got things wrong. Paste prompts **exactly** as you typed them.

## Tools I used

| Tool | Version or plan | What I used it for |
|---|---|---|
| [e.g. Cursor / Claude Code / GitHub Copilot / Gemini / ChatGPT] | [free / paid / version] | [schema, data layer, tests ...] |

## Log entries

Copy the block below for each entry.

---

### Entry [N]: [short title]

- **Date:** [YYYY-MM-DD]
- **Tool:** [tool and model, if shown]
- **Task (why I used AI here):** [what you delegated, and why you chose AI for it]
- **Prompt (verbatim):**

  ```text
  [paste the exact prompt]
  ```

- **What it produced:** [files changed or created, in one or two lines]
- **Decision:** Accepted / Modified / Rejected
- **Why:** [what made you accept, change or throw it away]
- **What I checked:** [how you verified it: read it field by field, ran tools/check_db.py, ran the tests, restarted the app ...]
- **Decisions the AI made that I did not specify:** [paste the answer to prompt 05, or "none"]
- **Commit:** [the commit message or hash where this landed]

---

### Entry [N]: Check the decisions the AI made on its own (prompt 05)

- **Date:** 2026-11-16
- **Tool:** Claude Code (Claude Opus 5.5)
- **Task (why I used AI here):** [why you asked the AI to list its own decisions]
- **Prompt (verbatim):**

  ```text
  Do not change any files. Look back over everything you have done in this conversation and
  in this project today.

  List every decision you made that I did not explicitly specify. Include names you chose,
  data types, limits, default values, delete behaviour (ON DELETE), error handling, libraries,
  file locations, and anything you removed or rewrote.

  Give me a table with these columns:
  | Decision | What you chose | What else you could have chosen | Why you chose it | Risk if it is wrong |

  Then tell me which ONE of these decisions you think I should check first, and why.
  ```

- **What it produced:** a table of 44 decisions it made on its own while building the data layer (`albumclub/db.py`), rewriting `albumclub/app.py`, the templates and `seed.py`, adding `schema/002_restrict_deletes.sql`, and writing `tests/test_constraints.py`. No files were changed. The rows below are a selection of those decisions.
- **Decision:** [Accepted / Modified / Rejected, overall]
- **Why:** [your overall view]
- **What I checked:** [e.g. read each row, compared it with AGENTS.md and docs/data-model.md, tried it in the running app]

- **Decisions the AI made that I did not specify:**

| Decision | What the AI chose | What else it could have chosen | Why it chose it | Risk if it is wrong | Keep / change / reject | My reason |
|---|---|---|---|---|---|---|

| How the album of the week is picked | 
When voting closes, the proposal with the most votes wins (a tie goes to the oldest). The losing proposals stay "approved" and go into next week's vote. The winner's `week_start` is changed to the week it won. | Losers become "rejected" each week; keep the original `week_start` |
 Keep |
 Going with the oldest seems fair, a first in, first choosen. Losing proposals have another chance next week of being picked. |

| Admins approving their own proposals |
 Allowed | 
 Block it (my specification says admins can't approve their own proposal) | Copied from the old version of the app | An admin can push their own albums through without anyone else agreeing |
 Reject |
 This isnt a fair way to have an album approved. It defeats the purpose of the voting mechanic. Membership status should not determine the choice for album of the week. |

| Joining an "invite only" club |
Anyone with the invite code becomes an active member straight away, for open and invite-only clubs alike | Invite-only clubs put new people in "pending" until an admin approves them | Kept the join page working the way it already did | The privacy setting doesn't actually change anything yet |
Keep |
An invite code is an approval by an already established member in teh club. It should be kept.  |

| When an album can be reviewed |
 As soon as it is approved | Only after it wins album of the week (the old app) | My data model says "after it has been approved" | Members can review albums the club hasn't listened to yet |
 Keep |
 Once an album has won the vote it should be reviewable. |

| A review that fails to save | Shows an error message, but whatever the member typed is lost | Show the form again with their text still in it | Copied the old app's pattern | 
Keep |
Annoying for members, and AGENTS.md says to keep people on the form | |

| Duplicate albums in a club | Same title and artist counts as a duplicate, ignoring capital letters | Exact match only, or title + artist + year | Catches "OK Computer" vs "ok computer" | Two different albums with the same name by the same artist (e.g. "Greatest Hits") are blocked |
Keep | 
People make human error spelling mistakes. The admin can catch these mistakes for the users.|

| Password length | At least 8 characters (stored scrambled using Werkzeug, which comes with Flask) | A different minimum, or a new library like bcrypt | Common minimum, and no new library 
Keep |
Common minimum, and no new library. For now it does not need to be stricter. |

**The AI's suggestion for what to check first:** how the album of the week is picked (the first row). The weekly cycle is the heart of the app, and this rule decides what the database remembers about past winners. If it's wrong, old data would need fixing, not just the code.

---

## Worked example (from the club equipment loans demo in Session 5)

### Entry 2: Generate the initial schema

- **Date:** 2026-11-11
- **Tool:** Claude Code
- **Task (why I used AI here):** turning my finished `docs/data-model.md` into SQL. I had already decided the tables and the delete rule myself; typing CREATE TABLE statements is the kind of mechanical job AI is good at.
- **Prompt (verbatim):**

  ```text
  Read docs/data-model.md and AGENTS.md. Create ONE file, schema/001_initial.sql, that builds
  exactly the tables, fields and rules in docs/data-model.md, using SQLite syntax. Do not
  change any other file. Do not add tables or fields I did not list. After the file, explain
  each constraint in one line of plain English, then list any decision you made that I did
  not specify.
  ```

- **What it produced:** `schema/001_initial.sql` with three tables (member, equipment, loan).
- **Decision:** Modified
- **Why:** it wrote `ON DELETE CASCADE` on both foreign keys even though my data model says RESTRICT. Cascade would wipe a member's loan history if they left the club, and the committee needs that history for insurance. I changed both to `ON DELETE RESTRICT`. It also added `AUTOINCREMENT`, which SQLite does not need here; I left that in and noted it.
- **What I checked:** read the SQL field by field against my data model (checklist in the lab guide), ran `python tools/migrate.py app.db`, then tried three bad inserts with `tools/sql.py`. The orphan loan got in until I used `--fk`, which led to the PRAGMA rule in AGENTS.md.
- **Decisions the AI made that I did not specify:** CASCADE on both foreign keys (changed), AUTOINCREMENT on ids (kept), `DEFAULT (date('now'))` on borrowed_on (kept).
- **Commit:** `Add initial schema from data model (delete rule: RESTRICT)`

> The tool responses in this worked example are illustrative of what agents commonly do. Your log must describe what YOUR tool actually did.
