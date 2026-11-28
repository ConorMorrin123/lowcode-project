# Task Management Application — Specification
 
## Purpose
A simple task tracker for a small team. Replaces a shared spreadsheet.
 
## Entities
### Task
- id (integer, primary key)
- title (text, required, max 200)
- description (text, optional)
- status (one of: todo, in_progress, done — default todo)
- created_at (timestamp)
- due_date (date, optional)
 
## Routes
| Method | Path | Does |
|---|---|---|
| GET  | / | List all tasks, newest first |
| GET  | /task/new | Form to create a task |
| POST | /task | Create a task, redirect to / |
| GET  | /task/<id> | Show one task |
| POST | /task/<id>/status | Change status, redirect back |
 
## Technical constraints
- Python 3.11+, Flask 3.x
- SQLite via the standard library sqlite3 (no ORM this week)
- Jinja2 templates in templates/, with one base template
- No authentication
- No JavaScript framework
 
## Out of scope
User accounts · reminders · file attachments · an API · search

---

## Prompt 6

> Could you create me a specification doc. Use the file doc2/specification.md. Use that template to populate for this project.

### Claude's full answer

I've written the Band Finder specification in `docs2/bandfinder-specification.md`.

**Where I put it, and why.** `docs2/specification.md` is the prompt log we've been keeping, so filling it with the spec would have wiped out the log. The template I followed is your album club spec, `docs/specification.md` (Purpose → Entities → Routes → Technical constraints → Out of scope). I saved the new spec next to the log in `docs2`. If you'd rather it went somewhere else (for example `bandfinder/docs/specification.md`), I can move it.

**What's in it**
- **Purpose:** what Band Finder is for and who uses it (18+ musicians in Ireland).
- **Users and roles:** visitor, member and admin.
- **Fixed dropdown lists:** instruments, genres, the 32 counties, skill level, age range, commitment and project type.
- **Entities:** User, Instrument, Genre, County, UserInstrument, UserGenre, Post, PostInstrument, PostGenre, Comment and Report, each with its fields and limits.
- **How they connect**, and a **Delete behaviour** table that is left blank for you to fill in.
- **"Suggested for you":** a simple points system (instrument match +3, same county +2, +1 per shared genre).
- **Pages and routes** for all seven pages, plus report and admin routes.
- **Look and feel:** a dark/light Spotify/GarageBand-style colour scheme with green on near-black.
- **Technical constraints**, **Out of scope** and an **Open questions** table.

**Still open.** The seven follow-ups (8a, 10a, 10b, 14a, 17a, 18a, 20a) and the delete rules are not answered yet. The spec shows the assumption I used for each in the Open questions table, so you can just say "agree" or change them.

**Decisions I made that you did not specify**
- Saved the spec as `docs2/bandfinder-specification.md` instead of overwriting the log, and used `docs/specification.md` as the template.
- The items in every dropdown list (instruments, genres, age ranges, project types), and all 32 counties of Ireland rather than only the 26 in the Republic.
- Separate lookup tables and link tables for instruments, genres and counties.
- Field limits: username 3–30 characters, display name 50, bio/influences/gear 500, post title 100, description 2000, comment 1000, years playing 0–80; social links must start with `https://`.
- 18+ is enforced with an "I am 18 or over" tick box at sign-up (self-declared).
- The first admin is created by a command-line script.
- Expired posts are hidden, not deleted.
- The "Suggested for you" points and showing the top 3.
- Route names and URL paths, and filters for skill level and commitment as well as instrument, genre and county.
- Passwords hashed with `werkzeug.security`; photos uploaded to `static/uploads/` (JPG/PNG, max 2 MB); a small bit of plain JavaScript for the theme toggle, remembered in the browser.
- Colour codes #121212 and #1DB954, and using the site's own branding rather than Spotify's or Apple's.
- The assumptions for the open questions (see the Open questions table).

### Short version

Claude wrote the spec in `docs2/bandfinder-specification.md`, using `docs/specification.md` as the template (it didn't overwrite the log). The spec covers purpose, roles, dropdown lists, 11 entities, connections, the matching rule, pages, routes, design, technical constraints and out of scope. Delete rules and seven follow-ups are still open, with assumptions listed.

---

## Prompt 7

> 8a. per instrument
> 10a. two dropdowns
> 10b. include
> 14a. 30 is the default and max
> 17a Social links only, also an optional public email or phone number
> 18a Yes admins can delete posts or comments. The comment is still their but the content of the comment is removed for users to see and a 'admin removed' tag is visible.
> 20a Yes include a simple admin page for maintenance.

### Claude's full answer

Thanks. I've updated `docs2/bandfinder-specification.md` with all seven answers:

- **8a. Skill per instrument:** skill level has moved from User to UserInstrument, so each instrument a person plays has its own level. The skill filter on the post list checks the poster's level on that instrument.
- **10a. Two dropdowns:** Commitment (Casual / Serious) and Project type are separate.
- **10b. Availability:** a new Availability dropdown on the profile (Weeknights, Weekends, Weeknights and weekends, Flexible).
- **14a. Expiry:** 30 days is the default and the maximum; posters may choose an earlier date.
- **17a. Contact:** social links, plus new optional PublicEmail and PublicPhone fields on the profile. The sign-up email stays hidden.
- **18a. Admin removals:** admins can delete any post. For comments, I added RemovedByAdmin and RemovedAt to Comment. The comment stays with its author, but other users see "Removed by admin" instead of the text.
- **20a. Admin page:** added as page 8, with routes to resolve reports, delete users, make admins, delete posts and remove comments. Non-admins get a 403 Forbidden page.

The "Open questions" table is now an "Answered follow-ups" table. The only thing left before I can build the database is the **delete behaviour**. For each one, choose **CASCADE** (delete the children too), **SET NULL** (keep them but empty the link, e.g. show "deleted user") or **RESTRICT** (block the delete while children exist):

1. A **user** is deleted → what happens to their **posts**?
2. A **user** is deleted → what happens to their **comments** on other people's posts?
3. A **user** is deleted → what happens to **reports they made** and **reports about them**?
4. A **user** is deleted → what happens to their **instrument and genre** choices?
5. A **post** is deleted → what happens to its **comments** and its instrument/genre tags?
6. An **instrument, genre or county** is removed from a dropdown list → what happens to the users and posts that use it?

**Decisions I made that you did not specify**
- The Availability options: Weeknights, Weekends, Weeknights and weekends, Flexible (one choice per person).
- Read 17a as "social links **plus** an optional public email and phone number". Phone is max 20 characters.
- When an admin removes a comment, the original text is kept in the database (hidden from users) so admins can still see it when checking a report.
- When an admin deletes a post, it is deleted (not hidden with a tag like comments). What happens to its comments depends on your answer to delete question 5.
- Added a "resolve report" admin route, and non-admins get a 403 page on admin routes.

### Short version

Spec updated: skill level per instrument; two goal dropdowns; availability added; 30-day default/max expiry; social links plus optional public email/phone; admins can delete posts and remove comments (shown as "Removed by admin"); a simple admin page. Only the six delete-behaviour questions remain before building the database.

---

## Prompt 8

> SET NULL. I want to see the records but specify that the user is deleted.

Claude then asked three follow-up questions in a pop-up (because SET NULL does not fit every case), and the answers were:

> - Q4 (user deleted → their instrument and genre choices): **CASCADE**
> - Q5 (post deleted → its comments and tags): **CASCADE**
> - Q6 (instrument, genre or county removed from a list → users and posts using it): **RESTRICT**

### Claude's full answer

Thanks. All the delete rules are now in the "Delete behaviour" table in `docs2/bandfinder-specification.md`, with your reasons:

| If this is deleted… | What happens to… | Your choice |
|---|---|---|
| A user | their posts | **SET NULL**: the post stays and shows "Deleted user" |
| A user | their comments | **SET NULL**: the comment stays and shows "Deleted user" |
| A user | reports they made, and reports about them | **SET NULL**: the report stays and shows "Deleted user" |
| A user | the instruments and genres on their profile | **CASCADE**: deleted with the account |
| A post | its comments and instrument/genre tags | **CASCADE**: deleted with the post |
| An instrument, genre or county | users and posts that use it | **RESTRICT**: it can't be removed while anything uses it |

I applied your SET NULL answer to questions 1–3, which are about a user's records. For 4–6 I asked you separately, because SET NULL would leave rows that never show anywhere (4 and 5), and a post's county is required, so it can't be emptied (6).

To make SET NULL work, the author link on posts and comments and both user links on reports are now allowed to be empty. An empty value is shown as "Deleted user".

The "Open questions" section now says none are left. The spec is complete, so the next step is to write `bandfinder/docs/data-model.md` and the first migration, `bandfinder/schema/001_initial.sql`, for you to check.

**Decisions I made that you did not specify**
- Applied your SET NULL answer to questions 1–3 only, and asked about 4–6 separately.
- The wording "Deleted user" for records whose user was deleted.
- One consequence of SET NULL: once the author is deleted, nobody can delete that post or comment except an admin.

### Short version

Delete rules decided: deleting a user keeps their posts, comments and reports with "Deleted user" shown (SET NULL), and removes their instrument/genre choices (CASCADE). Deleting a post removes its comments and tags (CASCADE). Dropdown items in use can't be removed (RESTRICT). The spec is complete; next is the data model and first migration.

---

## Prompt 9

> Yes, go ahead

### Claude's full answer

I've created the data model and the first database migration for Band Finder:

- **`bandfinder/docs/data-model.md`**: the source of truth for the database. It has every table with its columns and rules, how the tables connect, your delete rules with your reasons, the rules the app checks itself, and a diagram.
- **`bandfinder/schema/001_initial.sql`**: the SQL that builds the database. It creates 11 tables (county, instrument, genre, user, user_instrument, user_genre, post, post_instrument, post_genre, comment, report). It also fills the three dropdown lists: 32 counties, 13 instruments and 17 genres.

**How I checked it.** I applied the migration to a throwaway database in my scratch folder, not your project, using your existing tool. Running it a second time correctly skipped it. Then I tried to put bad data in, and the database rejected every attempt:
- a duplicate username
- someone who didn't tick 18+
- a link not starting with `https://`
- a made-up skill level
- a post expiring more than 30 days after it was posted
- a post with no county, and a post with a county that doesn't exist
- a removed comment without a removal date
- a user reporting themselves
- deleting a county that is in use

The delete rules also behaved as you chose. Deleting a user kept their post and report with the user link emptied ("Deleted user") and removed their instruments. Deleting a post removed its comments and tags.

**To build your own database**, run this from the `lowcode-project` folder:

    python tools/migrate.py bandfinder/app.db --schema bandfinder/schema

`*.db` files are already in `.gitignore`, so the database won't be committed.

**Not done yet:** `bandfinder/db.py` (with `get_connection()`), the proper `unittest` constraint tests, and the Flask app and pages.

**Decisions I made that you did not specify**
- Column names are lowercase with underscores (`user_id`, `expires_at`), matching your album club project, rather than the CamelCase names used in the spec.
- Reused your existing `tools/migrate.py` with `--schema bandfinder/schema`, instead of copying it into `bandfinder/`.
- The dropdown lists are filled in by the first migration, so they're always in the database.
- Dropdown values are stored as the text people see (for example `'Original band'`), not as codes.
- Link tables use a two-column primary key (for example `user_id` + `instrument_id`), which stops the same instrument being added twice.
- Email checks are simple (must contain `@`). Dates are stored as text, `YYYY-MM-DD HH:MM:SS`.
- The 30-day rule is checked in the database: `expires_at` must be after `created_at` and no more than 30 days later.
- `removed_at` must be filled in exactly when `removed_by_admin` is 1.
- No real `bandfinder/app.db` was created; the checks used a throwaway database.

### Short version

Created `bandfinder/docs/data-model.md` and `bandfinder/schema/001_initial.sql` (11 tables, with counties, instruments and genres filled in). Tested on a throwaway database: all bad-data attempts were rejected and the delete rules worked. Next: `db.py`, proper tests, then the Flask pages.

---

## Prompt 10

> Yes, go ahead

### Claude's full answer

I've added the database code and the tests for Band Finder. All 50 tests pass.

**`bandfinder/db.py`** holds all the database code, in the same style as your album club `db.py`:
- `get_connection()` is the one place that opens the database, and it always turns on `PRAGMA foreign_keys = ON`. It uses `bandfinder/app.db` unless `DATABASE_PATH` says otherwise.
- Functions for users and profiles, instruments and genres (with skill per instrument), posts (30-day expiry by default), comments (including an admin removing one), reports, and the dropdown lists.
- `list_open_posts()` hides expired posts and filters by instrument, genre, county, skill level and commitment.
- `suggested_posts()` works out the "Suggested for you" points and returns the best 3.
- Every query uses `?` placeholders. Even the filters do: each filter is written as "`? IS NULL OR …`", so an empty filter switches itself off and no SQL is ever pieced together.

**`bandfinder/tests/test_constraints.py`** has 50 tests. Each one uses a brand-new temporary database, never your real one. They cover:
- **Duplicates:** username, email, the same instrument twice, the same genre twice on a post, a repeated county.
- **CHECK rules:** under 18, short username, bad email, bad skill level, bad dropdown values, years playing out of range, `http://` links, a bio that is too long, expiry over 30 days or in the past, bad commitment, empty title, reporting yourself, bad report status, a removed comment with no date.
- **Missing required fields:** password, county, description, comment text, report reason.
- **Links to things that don't exist:** county, user, instrument, post and reported user.
- **Delete rules:** SET NULL for a deleted user's posts, comments and reports; CASCADE for their instruments/genres and for a post's comments and tags; RESTRICT for counties, instruments and genres in use.
- **Features:** an admin removing a comment, expired posts hidden, each filter, the "Suggested for you" ranking.
- **Data survives a restart:** data is still there after closing and reopening the file.

Run them from the `lowcode-project` folder with:

    python -m unittest discover -s bandfinder/tests -v

**Not checked:** pytest isn't installed on this computer, so I could only run the tests with `unittest`. They're written so they should also work under pytest.

**Decisions I made that you did not specify**
- `db.py` defaults to `bandfinder/app.db` and lets the `DATABASE_PATH` environment variable override it (the tests use this).
- Times are saved in UTC, in the same format SQLite uses.
- **Skill level filter:** it finds posts whose author plays any instrument at that level. The spec had said "the poster's level on the instrument", but a post usually wants an instrument the poster doesn't play, so I changed that line in the spec to match.
- "Suggested for you" leaves out posts that score 0, and your own posts. Ties go to the newest post.
- Saving instruments, genres or a post with its tags happens all at once: if one part fails, nothing is saved.
- The tests are in `bandfinder/tests/`, separate from the album club tests.

### Short version

Created `bandfinder/db.py` (`get_connection()` with foreign keys on, functions for users, posts, comments, reports, filters and "Suggested for you") and `bandfinder/tests/test_constraints.py` (50 tests, all passing under unittest; pytest isn't installed). The skill filter wording in the spec was adjusted. Next: the Flask app and pages.

---

## Prompt 11

> I was supposed to do my Git Branch before generating.

### Claude's full answer

Don't worry, nothing is lost and nothing needs undoing. None of the Band Finder work has been committed. Git sees `bandfinder/` and `docs2/` only as new, untracked files, and they aren't part of `main` yet. When you create and switch to a new branch, untracked files come with you. So making the branch now is the same as making it before I generated anything.

Run this from the `lowcode-project` folder (pick any branch name you like):

    git switch -c feature/bandfinder

Then commit on that branch as usual. `main` stays exactly as it is.

One thing to know: `docs/ux-ui-session-log.docx` (from your album club work) is also showing as changed. It will move to the new branch too. Only include it in your commit if you want it on this branch.

**Decisions I made that you did not specify**
- Suggested the branch name `feature/bandfinder`, following your earlier `feature/data-model` branch. I didn't create the branch myself.

### Short version

Nothing was committed, so creating the branch now (`git switch -c feature/bandfinder`) works exactly as if it had been made first. `docs/ux-ui-session-log.docx` also has uncommitted changes that will move with it.

---

## Prompt 12

> I'll do it myself

### Claude's full answer

Sounds good. Once you've created the branch, a quick `git branch --show-current` will confirm you're on it before you commit. When you're ready, tell me and I'll start on the Flask app and pages.

**Decisions I made that you did not specify**
- None.

### Short version

The user will create the Git branch themselves. Next step when they're ready: the Flask app and pages.

---

## Prompt 13

> start

### Claude's full answer

I've built the first working version of the Band Finder website. All 73 tests pass, and I checked every page in the browser.

**What I added (all in `bandfinder/`)**
- **`app.py`**: the Flask app with every route from the spec. That covers sign up / log in / log out, home, profile, edit profile, posts with filters, single post with comments, new post, report a user, and the admin page. Missing pages give a 404 page, members get a 403 page on admin pages, and anything the database rejects shows a friendly message instead of crashing.
- **`templates/`**: 13 HTML pages built on one shared layout (`base.html`), with a reusable "post card".
- **`static/style.css`**: the Spotify/GarageBand-style look. It has a near-black background with a green accent in dark mode, white/grey in light mode, rounded cards and pill-shaped tags. It also works on phones.
- **`static/theme.js`**: the dark/light toggle. The browser remembers your choice.
- **`make_admin.py`**: makes the first admin from the command line.
- **`tests/test_app.py`**: 23 new tests for the pages (on top of the 50 database tests).
- **`requirements.txt`** (Flask) and **`.gitignore`** (so uploaded photos aren't committed).

**How I checked it.** I built a demo database with sample users and posts in my scratch folder (not your project) and clicked through the site in the browser:
- landing page
- log in
- home with "Suggested for you" (match scores 7 and 3, as expected)
- a post with a "Removed by admin" comment
- filtering by county
- a profile in light mode (the choice stayed when changing page)
- the admin page
- the edit profile and new post forms on a phone-sized screen

There were no browser errors.

**How to run it yourself** (from the `lowcode-project` folder in PowerShell):

    python tools/migrate.py bandfinder/app.db --schema bandfinder/schema
    $env:SECRET_KEY = "type-any-long-random-text-here"
    .venv\Scripts\python.exe -m flask --app bandfinder/app.py run --debug

Then open http://127.0.0.1:5000, sign up, and make yourself admin with:

    .venv\Scripts\python.exe bandfinder/make_admin.py YOUR_USERNAME

Run all the tests with:

    .venv\Scripts\python.exe -m unittest discover -s bandfinder/tests -v

**Not done / not checked**
- pytest isn't installed, so the tests were only run with unittest.
- I didn't test uploading a real photo in the browser. The upload code is there, but no test covers it.
- Forms have no CSRF protection (a security token that stops other websites submitting forms as you). That's normal for a first class project, but it should be added before the site goes public.
- Nothing has been committed.

**Decisions I made that you did not specify**
- Log in uses **email + password** (not username).
- After signing up, you go straight to Edit profile.
- Passwords must be at least 8 characters.
- Visitors who aren't logged in only see the landing, sign up and log in pages.
- "Suggested for you" is shown on both the home page and the posts page (hidden on the posts page while filtering). The home page also shows the 6 newest posts.
- A post must ask for at least one instrument.
- **Expiry date:** you pick a day, and the post ends at 23:59 that day. Picking the 30th day uses the default "exactly 30 days".
- Posts are always deleted by their author or an admin. When an admin removes a comment, admins can still read the original text under the "Removed by admin" tag.
- Admins can't delete their own account from the admin page, so the site can't lose its last admin by accident.
- Photos get a random file name and are saved in `bandfinder/static/uploads/`. That folder is ignored by Git. Replacing or removing a photo deletes the old file.
- Dark mode is the default.
- Colours: green `#1DB954` (dark mode) / `#128A3E` (light mode, darker so it's easy to read), and orange for "Serious".
- Added `.claude/launch.json` so I could preview the site. It points at my scratch demo database, so you probably don't want to commit it.
- The first admin is made by promoting a signed-up user with `make_admin.py`, rather than creating a separate admin account.

### Short version

Built the Band Finder website: `app.py` (all routes), 13 templates, CSS with a dark/light toggle, `make_admin.py`, and 23 page tests (73 in total, all passing). Checked in the browser with demo data, including on mobile. Not done: photo upload test, CSRF protection, pytest run, commit.

---

## Prompt 14

> Track this in the ai-usage doc.
>
> Fix theses found issues:
> | 1 | app.py:176 | Usernames can contain `/`, which breaks that user's profile page | signed up as `a/b`, then `/user/a/b` gave 404 | Fix |
> | 2 | app.py:176 | Usernames that differ only in capitals are both allowed, so someone could pretend to be another user | created both `Aoife` and `aoife` | Fix |
> | 4 | app.py:253 | Photos are checked by file extension only, not by what's inside the file | by reading the code; low risk because files are served as images | Fix |
> | 5 | app.py:204 | No limit on wrong login attempts, so passwords can be guessed again and again | yes, by reading the code | Fix |

### Claude's full answer

I've fixed all four issues from the Week 3 review. All 89 tests pass: 73 old and 16 new.

**1. Usernames with `/` (or other odd characters)**
Usernames may now only use letters, numbers, `_` and `-` (still 3–30 characters).
- **App:** the sign-up form checks this and shows a friendly message. The username box also tells you the rule.
- **Database:** two triggers in a new migration refuse any other characters, even if the app has a bug.

**2. Usernames that differ only in capitals**
The database now treats "Aoife" and "aoife" as the same username, using a "no case" unique index. Signing up as `aoife` when `Aoife` exists shows "That username or email is already taken."

**4. Photos checked by name only**
The app now looks at the first bytes inside the file. Every real PNG and JPEG starts with a known "signature". A file that isn't really an image is refused with "Photos must be a real JPG or PNG image", whatever it's called. The saved file gets the extension of what it really is (a JPEG named `.png` is saved as `.jpg`).

**5. No limit on login attempts**
Wrong passwords are now recorded in a new `login_attempt` table (in the database, not in Python memory, as AGENTS.md requires). After 5 wrong attempts for one email within 15 minutes, logging in with that email is blocked, even with the right password, until the 15 minutes pass. A successful login clears the count.

**Files changed**
- New: `bandfinder/schema/002_username_rules_and_login_limits.sql` (I didn't edit `001`, because it has already been applied).
- `bandfinder/app.py`: username rule, login limit, photo check.
- `bandfinder/db.py`: four login-attempt functions.
- `bandfinder/templates/register.html`: username hint and pattern.
- `bandfinder/tests/`: 16 new tests (username characters and capitals, login lockout, fake vs real photos).
- `bandfinder/docs/data-model.md` and `docs2/bandfinder-specification.md`: updated to match.

**How I checked it**
- Ran all 89 tests. The photo tests save into a temporary folder, not `static/uploads/`.
- In the browser: 5 wrong passwords gave "Wrong email or password" and the 6th was blocked (status 429). The sign-up page shows the new username hint.

**What you need to do**
- If you already have a `bandfinder/app.db`, update it with:
  `python tools/migrate.py bandfinder/app.db --schema bandfinder/schema`
  If it already has two usernames that differ only in capitals, the migration stops and changes nothing. Rename one of them first.
- Nothing is committed. `docs2/week03-review.md` is unchanged, so you can fill in its Action column and "What I fixed" yourself.

**Decisions I made that you did not specify**
- Allowed characters: letters, numbers, `_` and `-`.
- Login limit: **5 wrong attempts per email in 15 minutes**, and the block applies even to the right password.
- Attempts are counted per email (not per computer/IP address), including emails that don't exist. Rows older than a day are deleted automatically.
- A blocked login returns status 429 ("Too Many Requests").
- Used database triggers for the username characters, because SQLite can't add a CHECK rule to an existing table without rebuilding it.
- The `login_attempt` table stores the email as text with no link to `user`, so no delete rule was needed.
- Photos are checked by their first bytes (PNG/JPEG signature). This doesn't check the whole image is valid.
- Profile web addresses still match the username exactly, with capitals: `/user/Aoife` works, `/user/aoife` gives 404.

### Short version

Fixed review items 1, 2, 4 and 5: usernames are limited to letters, numbers, `_` and `-`, and are unique ignoring capitals (migration `002` triggers + index); photos are checked by their real file signature; 5 wrong logins in 15 minutes blocks that email (new `login_attempt` table). 16 new tests, 89 passing, checked in the browser. Not committed.

---

## Prompt 15

> Fix this issue too: | 3 | app.py:396, db.py:37 | Mixes local time (`date.today()`) and UTC (`db.now()`), so expiry times and dates can be an hour out during Irish summer time | partly — by reading the code; only matters near midnight in summer | Fix |

### Claude's full answer

Fixed. All 100 tests pass (89 old and 11 new).

**The rule now:** the database always stores times in **UTC**, and anything a person sees or picks is in **Irish time**. A new file, `bandfinder/irish_time.py`, does every conversion between the two, so they can't get mixed up again.

**Why a new file instead of a library:** Python's built-in time zone feature (`zoneinfo`) has no time zone data on Windows unless you install an extra package (`tzdata`). Ireland's rule is short, so I wrote it out instead:
- Winter: Irish time = UTC.
- Summer: Irish time = UTC + 1 hour, from 01:00 UTC on the last Sunday of March to 01:00 UTC on the last Sunday of October.

**What changed in `app.py`**
- "Today" for the new-post date picker and the expiry checks is now **today in Ireland**, not the server's clock.
- A chosen expiry date now ends at **23:59:59 Irish time** that day, converted to UTC before it's saved. Before, it saved 23:59:59 UTC, which in summer is 00:59 the next morning in Ireland.
- Dates on pages ("28 Nov 2026") are shown as the **Irish date**. Before, a post made at 00:30 Irish time in summer showed the previous day.
- The date picker now starts at **tomorrow**, since today was never allowed anyway.
- The three copies of the new-post form code are now one helper, `new_post_page()`.

**Tests (`bandfinder/tests/test_irish_time.py`, 11 new)**
- the exact start and end of summer time in 2026
- a summer evening in UTC that's already the next day in Ireland
- end of an Irish day in UTC, in summer and in winter
- dates shown on pages
- a post's expiry saved at Irish midnight
- the 30-day maximum still holds, and today is refused

**Checked in the browser:** the new-post date picker allows 29 Nov to 28 Dec 2026, and post dates display correctly.

Not committed.

**Decisions I made that you did not specify**
- Times stay stored in UTC; only what people see and pick is in Irish time.
- Wrote the Irish summer-time rule myself instead of adding the `tzdata` library. If the EU ever changes the rule, `irish_time.py` would need updating.
- Picking the very last allowed day (30 days ahead) uses the default "exactly 30 days from now", so the post never goes past the database's 30-day limit.
- The date picker's first day is tomorrow (it was today, which was then refused).

### Short version

Fixed review item 3: new `bandfinder/irish_time.py` converts between UTC (stored) and Irish time (shown and picked), with summer time written out by hand (no extra library). Expiry dates now end at Irish midnight and pages show Irish dates. 11 new tests, 100 passing, checked in the browser. Not committed.
