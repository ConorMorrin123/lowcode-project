# Task Management Application — Specification
 
## Purpose
A private app for small music-loving groups, such as friends, a university society or a workplace
listening club. It replaces the usual group-chat chaos of "what should we listen to this week?" with a
structured weekly cycle: members propose albums, an admin approves them, the club votes, and the
winner becomes the album of the week. Everyone then rates and reviews it. Each club's data is
visible only to its own members.
 
## Entities
### User
- UserID (integer, primary key)
- Name (text, required, max 200)
- Email (text, required)

### Membership
- MembershipID (integer, primary key)
- ClubID (integer, foregin key)
- UserID (integer, foregin key)
- JoinedAt ()

### Club
- ClubID (integer, primary key)
- Name (text, required, max 200)
- JoinCode (text, required, max 100)

### Vote
- VoteID (integer, primary key)
- ProposalID (integer, foregin key)
- UserID (integer, foregin key)
- ClubID (integer, foregin key)
- CastAt ()

### Proposal
- ProposalID (integer, primary key)
- ClubID (integer, primary key)
- AlbumID (integer, foregin key)
- ProposedBy ()
- Pitch (text, max 200)
- Status ()

### Album
- AlbumID (integer, primary key)
- Title (text, required)
- Artist (text, required)
- Year (integer, required)
- Genre (text, required)

### Review
- ReviewID (integer, primary key)
- ProposalID (integer, foregin key)
- UserID (integer, foregin key)
- ClubID (integer, foregin key)
- Rating (integer, required)
- Comment (text, optional)
 
## Routes
| Method | Path | Does |
|---|---|---|
| GET | / | List all tasks, newest first |
| GET | /task/new | Form to create a task |
| POST | /task | Create a task, redirect to / |
| GET | /task/<id> | Show one task |
| POST | /task/<id>/status | Change status, redirect back |
 
## Technical constraints
- Python 3.11+, Flask 3.x
- SQLite via the standard library `sqlite3` (no ORM this week)
- Jinja2 templates in `templates/`, one base template
- No authentication this week
- No JavaScript framework
 
## Out of scope
- Streaming or playing music, and any Spotify or other API integration
- A recommendation engine or algorithmic suggestions
- Public clubs, social feeds, followers or discovery between clubs
- A native mobile app, offline use, or push notifications
