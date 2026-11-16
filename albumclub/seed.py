"""Seed the Album Club database with demo data.

The database must already have its tables (python tools/migrate.py app.db).
Every demo user gets the same password, taken from the SEED_PASSWORD
environment variable so no password is typed into this file.

Usage (from the top project folder, venv active):
    Windows PowerShell:  $env:SEED_PASSWORD = "pick-a-password"
    Mac / Git Bash:      export SEED_PASSWORD="pick-a-password"
    python albumclub/seed.py            # seeds an empty database
    python albumclub/seed.py --reset    # wipes all data first, then seeds
"""
import os
import sys
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

import db


def weeks_ago(club_day, n):
    """The start of the week n weeks before this club's current week."""
    current = date.fromisoformat(db.current_week_start(club_day))
    return (current - timedelta(weeks=n)).isoformat()


def wipe():
    """Delete all app data (children first). The tables themselves stay."""
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM review")
        conn.execute("DELETE FROM vote")
        conn.execute("DELETE FROM proposal")
        conn.execute("DELETE FROM album")
        conn.execute("DELETE FROM membership")
        conn.execute("DELETE FROM club")
        conn.execute("DELETE FROM user")
        conn.commit()
    finally:
        conn.close()


def seed(password):
    password_hash = generate_password_hash(password)

    # ---------------------------------------------------------- users
    people = [
        ("aoife", "aoife@example.com", "Classic rock and soft rock"),
        ("ciaran", "ciaran@example.com", "Indie and psych pop"),
        ("niamh", "niamh@example.com", "R&B and indie rock"),
        ("sean", "sean@example.com", "Hip hop and trip hop"),
        ("priya", "priya@example.com", None),
        ("dara", "dara@example.com", "Shoegaze"),
    ]
    user = {}
    for username, email, taste in people:
        user[username] = db.create_user(username, email, password_hash, taste)

    # ---------------------------------------------------------- clubs
    def make_club(name, description, code, privacy, day, admin, members):
        club_id = db.create_club(name, description, code, privacy, day, user[admin])
        for who in members:
            db.create_membership(user[who], club_id, "member", "active")
        return club_id

    friday = make_club("Friday Listening Club", "Friends picking one album a week.",
                       "FRIDAY-CLUB", "invite_only", "Friday", "aoife",
                       ["ciaran", "niamh", "sean", "priya"])
    vinyl = make_club("Campus Vinyl Society", "The university vinyl society's weekly spin.",
                      "VINYL-SOC", "open", "Monday", "priya", ["ciaran", "dara"])

    # --------------------------------------------------------- helpers
    def proposal(club, title, artist, year, genre, by, status, week, admin=None):
        album_id = db.create_album(club, title, artist, genre, year)
        proposal_id = db.create_proposal(club, album_id, user[by], week)
        if status != "pending":
            db.update_proposal_status(proposal_id, status, user[admin])
        return proposal_id, album_id

    def review(album_id, who, rating, text):
        db.create_review(album_id, user[who], rating, text)

    # ------------------------------------------ Friday Listening Club
    fri_now = db.current_week_start("Friday")

    _, rumours = proposal(friday, "Rumours", "Fleetwood Mac", 1977, "Rock",
                          "aoife", "winner", weeks_ago("Friday", 2), "aoife")
    review(rumours, "aoife", 5, "Timeless. Go Your Own Way still gives me chills.")
    review(rumours, "ciaran", 4, "Great harmonies, a couple of slower middle tracks.")
    review(rumours, "niamh", 5, "Every song is a single.")
    review(rumours, "sean", 4, "Dreams is the standout for me.")
    review(rumours, "priya", 5, "Pure comfort listening.")

    _, blonde = proposal(friday, "Blonde", "Frank Ocean", 2016, "R&B",
                         "niamh", "winner", weeks_ago("Friday", 1), "aoife")
    review(blonde, "aoife", 5, "Nights is a masterpiece of a two-parter.")
    review(blonde, "ciaran", 4, "Slow burner, but it really grew on me.")
    review(blonde, "priya", 5, "Beautiful from start to finish.")
    # niamh and sean haven't reviewed yet, so they can try the review form

    is_this_it, _ = proposal(friday, "Is This It", "The Strokes", 2001, "Indie Rock",
                             "niamh", "approved", fri_now, "aoife")
    currents, _ = proposal(friday, "Currents", "Tame Impala", 2015, "Psychedelic Pop",
                           "ciaran", "approved", fri_now, "aoife")
    mezzanine, _ = proposal(friday, "Mezzanine", "Massive Attack", 1998, "Trip Hop",
                            "sean", "approved", fri_now, "aoife")
    db.create_vote(friday, currents, user["aoife"], fri_now)
    db.create_vote(friday, currents, user["ciaran"], fri_now)
    db.create_vote(friday, is_this_it, user["niamh"], fri_now)
    db.create_vote(friday, mezzanine, user["priya"], fri_now)
    # sean hasn't voted yet

    proposal(friday, "Punisher", "Phoebe Bridgers", 2020, "Indie Folk",
             "priya", "pending", fri_now)
    proposal(friday, "To Pimp a Butterfly", "Kendrick Lamar", 2015, "Hip Hop",
             "sean", "pending", fri_now)

    # ------------------------------------------ Campus Vinyl Society
    mon_now = db.current_week_start("Monday")

    _, dummy = proposal(vinyl, "Dummy", "Portishead", 1994, "Trip Hop",
                        "dara", "winner", weeks_ago("Monday", 1), "priya")
    review(dummy, "priya", 5, "Atmospheric from start to finish.")
    review(dummy, "ciaran", 4, "Best on vinyl with the lights down low.")

    pet_sounds, _ = proposal(vinyl, "Pet Sounds", "The Beach Boys", 1966, "Pop",
                             "ciaran", "approved", mon_now, "priya")
    kid_a, _ = proposal(vinyl, "Kid A", "Radiohead", 2000, "Art Rock",
                        "priya", "approved", mon_now, "priya")
    db.create_vote(vinyl, kid_a, user["dara"], mon_now)
    db.create_vote(vinyl, pet_sounds, user["ciaran"], mon_now)

    proposal(vinyl, "Loveless", "My Bloody Valentine", 1991, "Shoegaze",
             "dara", "pending", mon_now)


def main():
    password = os.environ.get("SEED_PASSWORD")
    if not password:
        print("Please set the SEED_PASSWORD environment variable first (see the top of seed.py).")
        return

    reset = "--reset" in sys.argv
    conn = db.get_connection()
    try:
        has_data = conn.execute("SELECT COUNT(*) FROM user").fetchone()[0] > 0
    finally:
        conn.close()
    if has_data and not reset:
        print("The database already has data. Run `python albumclub/seed.py --reset` to wipe and reseed.")
        return
    if reset:
        wipe()
    seed(password)
    print("Demo data loaded. Log in as aoife, ciaran, niamh, sean, priya or dara with SEED_PASSWORD.")


if __name__ == "__main__":
    main()
