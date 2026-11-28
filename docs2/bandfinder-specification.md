# Band Finder — Specification

## Purpose
Band Finder is a website for musicians in Ireland who want to find band mates or people to jam with.
Sites like Boards.ie and Bandcamp feel dated and are hard to navigate for this. Band Finder gives each
musician a simple profile (instruments, genres, skill level, influences, county) and a modern posting
forum where people say who they are looking for. Posts can be filtered by instrument, genre and county,
and a "Suggested for you" section at the top of the page shows the posts that best match the
logged-in user. People reply in a comment section under each post and contact each other through
the links on their profiles. Users must be 18 or over.

## Users and roles
- **Visitor (not logged in):** sees the landing page, sign up and log in only.
- **Member (logged in):** edits their own profile, browses and filters posts, creates posts,
  comments on posts and reports users.
- **Admin:** everything a member can do, plus deleting users and other admins, making other
  users admins, deleting posts and removing comments. Only an admin can create another admin.
  The first admin is created with a command-line script, not through the website. Admins do
  this from a simple admin page.

## Fixed dropdown lists
These are stored in their own lookup tables, so the dropdowns and filters always use the same values.
- **Instrument:** Lead guitar, Rhythm guitar, Bass, Drums, Vocals, Backing vocals, Keyboard / Piano,
  Synth, Violin, Saxophone, Trumpet, DJ / Electronics, Other
- **Genre:** Rock, Indie, Alternative, Punk, Metal, Pop, Folk, Trad / Irish, Blues, Jazz, Funk, Soul / R&B,
  Hip hop, Electronic, Country, Reggae, Covers / Mixed
- **County:** the 32 counties of Ireland
- **Skill level:** Beginner, Intermediate, Advanced, Pro
- **Age range:** 18–24, 25–34, 35–44, 45–54, 55+
- **Commitment:** Casual, Serious
- **Project type:** Original band, Covers band, Wedding / function band, Jam only, Session work
- **Availability:** Weeknights, Weekends, Weeknights and weekends, Flexible

Commitment and Project type are two separate dropdowns.

## Entities

### User
- UserID (integer, primary key)
- Username (text, required, unique, 3–30 characters)
- Email (text, required, unique, never shown publicly)
- PasswordHash (text, required, the password is stored hashed, never as plain text)
- IsAdmin (integer, required, 0 or 1, default 0)
- ConfirmedAdult (integer, required, must be 1: the "I am 18 or over" box at sign up)
- DisplayName (text, optional, max 50)
- PhotoPath (text, optional, the file name of an uploaded photo)
- Bio (text, optional, max 500)
- AgeRange (text, optional, one of the age range list)
- YearsPlaying (integer, optional, 0–80)
- Influences (text, optional, max 500, favourite bands and influences)
- Gear (text, optional, max 500)
- CountyID (integer, optional, foreign key to County)
- Commitment (text, optional, Casual or Serious)
- ProjectType (text, optional, one of the project type list)
- Availability (text, optional, one of the availability list)
- SoundCloudURL, YouTubeURL, SpotifyURL, InstagramURL (text, optional, must start with `https://`)
- PublicEmail (text, optional, a contact email shown on the profile; separate from the sign-up email)
- PublicPhone (text, optional, max 20, shown on the profile)
- CreatedAt (text, required, date and time the account was made)

### Instrument
- InstrumentID (integer, primary key)
- Name (text, required, unique)

### Genre
- GenreID (integer, primary key)
- Name (text, required, unique)

### County
- CountyID (integer, primary key)
- Name (text, required, unique)

### UserInstrument (which instruments a user plays, and how well)
- UserID (integer, foreign key to User)
- InstrumentID (integer, foreign key to Instrument)
- SkillLevel (text, required, one of the skill level list; set per instrument)
- The pair (UserID, InstrumentID) is unique

### UserGenre (which genres a user likes)
- UserID (integer, foreign key to User)
- GenreID (integer, foreign key to Genre)
- The pair (UserID, GenreID) is unique

### Post
- PostID (integer, primary key)
- UserID (integer, foreign key to User, the person who posted; empty if the user was deleted)
- Title (text, required, max 100)
- Description (text, required, max 2000)
- CountyID (integer, required, foreign key to County)
- Commitment (text, required, Casual or Serious)
- CreatedAt (text, required)
- ExpiresAt (text, required, no later than 30 days after CreatedAt)

### PostInstrument (instruments the post is looking for)
- PostID (integer, foreign key to Post)
- InstrumentID (integer, foreign key to Instrument)
- The pair (PostID, InstrumentID) is unique

### PostGenre (genres of the post)
- PostID (integer, foreign key to Post)
- GenreID (integer, foreign key to Genre)
- The pair (PostID, GenreID) is unique

### Comment
- CommentID (integer, primary key)
- PostID (integer, foreign key to Post)
- UserID (integer, foreign key to User, the person who commented; empty if the user was deleted)
- Body (text, required, max 1000)
- CreatedAt (text, required)
- RemovedByAdmin (integer, required, 0 or 1, default 0)
- RemovedAt (text, optional, when an admin removed it)

When an admin removes a comment, the comment row stays and still belongs to its author. Other
users see "Removed by admin" instead of the text. The original text is kept in the database so
admins can still see it (for example when checking a report).

### Report
- ReportID (integer, primary key)
- ReporterID (integer, foreign key to User, the person reporting; empty if that user was deleted)
- ReportedUserID (integer, foreign key to User, the person being reported; empty if that user was deleted)
- Reason (text, required, max 1000)
- Status (text, required, Open or Resolved, default Open)
- CreatedAt (text, required)
- A user cannot report themselves (ReporterID must not equal ReportedUserID)

## How the entities connect
- A User plays many Instruments, each at its own skill level (through UserInstrument), and likes
  many Genres (through UserGenre).
- A User lives in one County (optional).
- A User writes many Posts. Each Post belongs to one User and one County.
- A Post looks for many Instruments and has many Genres (through PostInstrument and PostGenre).
- A Post has many Comments. Each Comment belongs to one Post and one User.
- A User can make many Reports and can be reported many times.

## Delete behaviour
These are your business decisions.
| If this is deleted… | What happens to… | Your choice | Why |
|---|---|---|---|
| A User | their Posts | SET NULL | You want to keep the records. The post stays and shows "Deleted user" as the author |
| A User | their Comments on other people's posts | SET NULL | Same reason. The comment stays and shows "Deleted user" |
| A User | Reports they made, and Reports about them | SET NULL | Same reason. The report stays and shows "Deleted user" |
| A User | their UserInstrument / UserGenre rows | CASCADE | These only describe that person's profile, so they go with the account |
| A Post (by its author or an admin) | its Comments, PostInstrument and PostGenre rows | CASCADE | Comments and tags have no meaning without their post |
| An Instrument, Genre or County | Users and Posts that use it | RESTRICT | The item can't be removed from a list while anyone still uses it |

Because of the SET NULL choices, Post.UserID, Comment.UserID, Report.ReporterID and
Report.ReportedUserID are allowed to be empty (NULL). An empty value means "Deleted user".

## Business rules
- Users must tick "I am 18 or over" to sign up.
- Username and email must each be unique.
- Only the logged-in user can edit their own profile and delete their own posts and comments.
- A post expires 30 days after it is created by default. The poster may choose an earlier date,
  but never later than 30 days. Expired posts are hidden from the post list and from
  "Suggested for you", but are not deleted.
- Only admins can create admins, and only admins can delete users and admins.
- Admins can delete any post and remove any comment. A removed comment shows "Removed by admin".
- A user's sign-up email is never shown to other users. Contact is through social links and the
  optional public email and phone number on the profile.

## "Suggested for you"
A simple, rule-based match, not an AI system. For the logged-in user, each open post gets points:
- +3 if the post wants an instrument the user plays
- +2 if the post is in the user's county
- +1 for each genre the post shares with the user

The highest-scoring posts (top 3, not the user's own) are shown at the top of the home page and the post list.

## Pages (version one)
1. Home / landing page (with "Suggested for you" when logged in)
2. Sign up / log in
3. Profile page
4. Edit profile
5. List of posts with filters
6. Single post page (with comments)
7. Create post page
8. Admin page (simple maintenance: reports, users, removing posts and comments)

## Routes

## Account
| Method | Path | Does |
|---|---|---|
| GET | /register | Sign up form |
| POST | /register | Create a user, redirect to /login |
| GET | /login | Log in form |
| POST | /login | Log in, redirect to / |
| POST | /logout | Log out, redirect to / |

## Home
| Method | Path | Does |
|---|---|---|
| GET | / | Landing page for visitors. For logged-in users: "Suggested for you" and the newest posts |

## Profile
| Method | Path | Does |
|---|---|---|
| GET | /user/<username> | Show one user's profile (404 if they don't exist) |
| GET | /me/edit | Form to edit your own profile |
| POST | /me | Save your own profile, redirect to /user/<username> |

## Post
| Method | Path | Does |
|---|---|---|
| GET | /posts | List open posts. Filters: ?instrument=, ?genre=, ?county=, ?skill=, ?commitment= (skill matches posts whose author plays any instrument at that level) |
| GET | /posts/new | Form to create a post |
| POST | /posts | Create a post, redirect to /posts/<post_id> |
| GET | /posts/<post_id> | Show one post and its comments (404 if it doesn't exist) |
| POST | /posts/<post_id>/delete | Delete your own post, redirect to /posts |

## Comment
| Method | Path | Does |
|---|---|---|
| POST | /posts/<post_id>/comments | Add a comment, redirect to /posts/<post_id> |
| POST | /comments/<comment_id>/delete | Delete your own comment, redirect back to the post |

## Report
| Method | Path | Does |
|---|---|---|
| GET | /user/<username>/report | Form to report a user |
| POST | /user/<username>/report | Save the report, redirect to /user/<username> with a thank-you message |

## Admin
| Method | Path | Does |
|---|---|---|
| GET | /admin | Admin page: open reports and the list of users (admins only) |
| POST | /admin/users/<user_id>/delete | Delete a user or admin (admins only) |
| POST | /admin/users/<user_id>/make-admin | Make a user an admin (admins only) |
| POST | /admin/reports/<report_id>/resolve | Mark a report as Resolved (admins only) |
| POST | /admin/posts/<post_id>/delete | Delete any post (admins only) |
| POST | /admin/comments/<comment_id>/remove | Hide a comment's text and show "Removed by admin" (admins only) |

Anyone who is not an admin gets a 403 Forbidden page on these routes.

## Look and feel
- Colour feel inspired by Spotify and GarageBand: a near-black background (#121212) with a bright
  green accent (#1DB954) in dark mode, and a white / light grey background with the same green in
  light mode. The site uses its own name and logo, not Spotify's or Apple's branding.
- A dark / light mode toggle in the top bar. The choice is remembered in the browser.
- Posts and profiles are shown as rounded cards, and the layout works on phones as well as desktop.

## Technical constraints
- Python 3.11+, Flask 3.x
- SQLite via the standard library `sqlite3` (no ORM)
- All files live in `bandfinder/`
- Schema in numbered migration files in `bandfinder/schema/`, applied with `python tools/migrate.py`
- One `get_connection()` in `bandfinder/db.py` that turns on `PRAGMA foreign_keys = ON`
- Only parameterised (`?`) queries
- Jinja2 templates in `bandfinder/templates/`, one base template
- Plain HTML and CSS. A few lines of plain JavaScript only for the dark / light toggle. No JavaScript framework
- Passwords hashed with `werkzeug.security` (comes with Flask)
- `SECRET_KEY` comes from an environment variable, never from the code
- Profile photos uploaded to `bandfinder/static/uploads/` (JPG or PNG, max 2 MB)
- Tests with `unittest`, using a temporary database

## Out of scope (version one)
- Private messaging between users (contact is through profile links, public email or phone)
- Blocking users
- Email notifications, email verification and password reset by email
- Locations more precise than county, or distance search
- Playing music on the site or connecting to the Spotify, YouTube or SoundCloud APIs
- Proof of age (age is self-declared)
- A native mobile app or push notifications

## Answered follow-ups
| # | Question | Your answer |
|---|---|---|
| 8a | Skill level per person or per instrument? | Per instrument |
| 10a | Goals as two dropdowns or one list? | Two dropdowns (Commitment, Project type) |
| 10b | Include availability? | Yes |
| 14a | Post expiry | 30 days is the default and the maximum |
| 17a | Contact details | Social links, plus an optional public email and phone number |
| 18a | Can admins delete posts and comments? | Yes. A removed comment stays with its author but its text is hidden and "Removed by admin" is shown |
| 20a | Admin page? | Yes, a simple admin page for maintenance |

## Open questions
None. All questions are answered.
