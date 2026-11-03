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
## User
| Method | Path | Does |
| GET | /register | Form to create an account |
| POST | /user | Create a user, redirect to /login |
| GET | /login | Sign-in form |
| POST | /login | Sign in, redirect to / |
| POST | /logout | Sign out, redirect to /login |
| GET | /me | Show your own profile |
| POST | /me | Update your own name or email, redirect to /me |

## Club
| Method | Path | Does |
| GET | / | List the clubs you belong to |
| POST | /club/new | Form to create a club |
| POST | /club | Create a club and make the creator its Admin, redirect to /club/<club_id> |
| GET | /club/<club_id> | Show one club: current pick, open proposals (members only) |
| GET | /club/<club_id>/join-code | Generate a new join code, redirect back (Admin only) |
| POST | /club/<club_id>/delete | Delete the club and its data, redirect to / (Admin only) |

## Membership
| Method | Path | Does |
| GET | /join | Form to enter a join code |
| POST | /join | Create a Membership as Member, redirect to /club/<club_id> |
| GET | /club/<club_id>/members | List members (only Admins see emails) |
| POST | /club/<club_id>/members/<membership_id>/role | Change a member’s role, redirect back (Admin only) |
| POST | /club/<club_id>/members/<membership_id>/remove	 | Remove a member, redirect back (Admin only) |
| POST | /club/<club_id>/leave | Show your own profile |
| POST | /me | Leave the club (your own Membership), redirect to / |

## Album
| Method | Path | Does |
| GET | /album/search | Search existing albums by title or artist |
| GET | /album/new | Form to add an album that isn’t listed yet |
| POST | /album | Create an album, redirect to the new proposal form |
| GET | /album/<album_id> | Show one album and its details |

## Proposal
| Method | Path | Does |
| GET | /club/<club_id>/proposals | List the club’s proposals, filterable by status |
| POST | /club/<club_id>/proposal/new | Form to propose an album |
| POST | /club/<club_id>/proposal | Create a proposal as Pending, notify the Admin, redirect to /club/<club_id>/proposals |
| GET | /proposal/<proposal_id> | Show one proposal with its vote count and reviews |
| POST | /proposal/<proposal_id>/status | Approve or reject a proposal, redirect back (Admin only, not your own proposal) |
| POST | /proposal/<proposal_id>/withdraw | Withdraw your own proposal while it is Pending, redirect to /club/<club_id>/proposals |

## Vote
| Method | Path | Does |
| POST | /proposal/<proposal_id>/vote | Cast your vote, redirect back (one per member, only while the proposal is Approved and voting is open) |
| GET | /club/<club_id>/pick | Show the current album of the week and the latest results |

## Review
| Method | Path | Does |
| GET | /proposal/<proposal_id>/review/new | Form to review a picked album |
| POST | /proposal/<proposal_id>/review | Create your review, redirect to /proposal/<proposal_id> (one per member, Picked proposals only) |
| GET | /review/<review_id>/edit | Form to edit your own review |
| POST | /review/<review_id> | Update your own review, redirect to /proposal/<proposal_id> |
| POST | /review/<review_id>/delete | Delete a review, redirect back (the author, or an Admin of that club) |
 
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
