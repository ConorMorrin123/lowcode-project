"""Seed the Album Club database with demo data.

Usage (from the albumclub/ folder, venv active):
    python seed.py            # seeds an empty database
    python seed.py --reset    # wipes all data first, then seeds
"""
import sys
from datetime import datetime, timedelta, timezone

from app import app
import db


def ts(days_ago=0, hours_ago=0):
    t = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_ago)
    return t.isoformat(timespec="seconds")


def wipe(conn):
    for table in ("Review", "Vote", "Proposal", "Album", "Membership", "Club", "User"):
        conn.execute(f"DELETE FROM {table}")
    conn.execute("DELETE FROM sqlite_sequence")


def seed(conn):
    # ---------------------------------------------------------- users
    people = [
        ("aoife", "Aoife Murphy", "aoife@example.com"),
        ("ciaran", "Ciaran Byrne", "ciaran@example.com"),
        ("niamh", "Niamh Kelly", "niamh@example.com"),
        ("sean", "Sean Doyle", "sean@example.com"),
        ("priya", "Priya Nair", "priya@example.com"),
        ("dara", "Dara Walsh", "dara@example.com"),
    ]
    user = {}
    for key, name, email in people:
        cur = conn.execute("INSERT INTO User (Name, Email) VALUES (?, ?)", (name, email))
        user[key] = cur.lastrowid

    # ---------------------------------------------------------- clubs
    def make_club(name, code, members):
        cur = conn.execute("INSERT INTO Club (Name, JoinCode) VALUES (?, ?)", (name, code))
        club_id = cur.lastrowid
        for i, (key, role) in enumerate(members):
            conn.execute(
                "INSERT INTO Membership (ClubID, UserID, Role, JoinedAt) VALUES (?, ?, ?, ?)",
                (club_id, user[key], role, ts(days_ago=30 - i)))
        return club_id

    friday = make_club("Friday Listening Club", "FRIDAY-CLUB", [
        ("aoife", "admin"), ("ciaran", "member"), ("niamh", "member"),
        ("sean", "member"), ("priya", "member")])
    vinyl = make_club("Campus Vinyl Society", "VINYL-SOC", [
        ("priya", "admin"), ("ciaran", "member"), ("dara", "member")])

    # --------------------------------------------------------- helpers
    def album(title, artist, year, genre):
        cur = conn.execute(
            "INSERT INTO Album (Title, Artist, Year, Genre) VALUES (?, ?, ?, ?)",
            (title, artist, year, genre))
        return cur.lastrowid

    def proposal(club, alb, by, pitch, status, won_days_ago=None):
        won_at = ts(days_ago=won_days_ago) if won_days_ago is not None else None
        cur = conn.execute(
            """INSERT INTO Proposal (ClubID, AlbumID, ProposedBy, Pitch, Status, WonAt)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (club, alb, user[by], pitch, status, won_at))
        return cur.lastrowid

    def vote(club, prop, who):
        conn.execute(
            "INSERT INTO Vote (ProposalID, UserID, ClubID, CastAt) VALUES (?, ?, ?, ?)",
            (prop, user[who], club, ts(hours_ago=5)))

    def review(club, prop, who, rating, comment=None):
        conn.execute(
            "INSERT INTO Review (ProposalID, UserID, ClubID, Rating, Comment) VALUES (?, ?, ?, ?, ?)",
            (prop, user[who], club, rating, comment))

    # ------------------------------------------ Friday Listening Club
    rumours = proposal(friday, album("Rumours", "Fleetwood Mac", 1977, "Rock"),
                       "aoife", "Peak songwriting drama, and every track is a hit.",
                       "won", won_days_ago=14)
    review(friday, rumours, "aoife", 5, "Timeless. Go Your Own Way still gives me chills.")
    review(friday, rumours, "ciaran", 4, "Great harmonies, a couple of slower middle tracks.")
    review(friday, rumours, "niamh", 5)
    review(friday, rumours, "sean", 4, "Dreams is the standout for me.")
    review(friday, rumours, "priya", 5, "Pure comfort listening.")

    blonde = proposal(friday, album("Blonde", "Frank Ocean", 2016, "R&B"),
                      "niamh", "Intimate, experimental and endlessly replayable.",
                      "won", won_days_ago=7)
    review(friday, blonde, "aoife", 5, "Nights is a masterpiece of a two-parter.")
    review(friday, blonde, "ciaran", 4, "Slow burner, but it really grew on me.")
    review(friday, blonde, "priya", 5)
    # niamh and sean haven't reviewed yet, so they can try the review form

    is_this_it = proposal(friday, album("Is This It", "The Strokes", 2001, "Indie Rock"),
                          "niamh", "Garage-rock cool in just 36 minutes.", "approved")
    currents = proposal(friday, album("Currents", "Tame Impala", 2015, "Psychedelic Pop"),
                        "ciaran", "Dreamy synths with big pop hooks.", "approved")
    mezzanine = proposal(friday, album("Mezzanine", "Massive Attack", 1998, "Trip Hop"),
                         "sean", "Dark, cinematic and perfect for a late-night listen.", "approved")
    vote(friday, currents, "aoife")
    vote(friday, currents, "ciaran")
    vote(friday, is_this_it, "niamh")
    vote(friday, mezzanine, "priya")
    # sean hasn't voted yet

    proposal(friday, album("Punisher", "Phoebe Bridgers", 2020, "Indie Folk"),
             "priya", "Sad songs with a sharp sense of humour.", "pending")
    proposal(friday, album("To Pimp a Butterfly", "Kendrick Lamar", 2015, "Hip Hop"),
             "sean", "Jazz, funk and poetry in one huge album.", "pending")

    # ------------------------------------------ Campus Vinyl Society
    dummy = proposal(vinyl, album("Dummy", "Portishead", 1994, "Trip Hop"),
                     "dara", "Best on vinyl with the lights down low.",
                     "won", won_days_ago=10)
    review(vinyl, dummy, "priya", 5, "Atmospheric from start to finish.")
    review(vinyl, dummy, "ciaran", 4)

    pet_sounds = proposal(vinyl, album("Pet Sounds", "The Beach Boys", 1966, "Pop"),
                          "ciaran", "The album that inspired Sgt. Pepper.", "approved")
    kid_a = proposal(vinyl, album("Kid A", "Radiohead", 2000, "Art Rock"),
                     "priya", "Radiohead's electronic left turn.", "approved")
    vote(vinyl, kid_a, "dara")
    vote(vinyl, pet_sounds, "ciaran")

    proposal(vinyl, album("Loveless", "My Bloody Valentine", 1991, "Shoegaze"),
             "dara", "A wall of beautiful noise.", "pending")


def main():
    reset = "--reset" in sys.argv
    with app.app_context():
        conn = db.get_db()
        has_data = conn.execute("SELECT COUNT(*) FROM User").fetchone()[0] > 0
        if has_data and not reset:
            print("The database already has data. Run `python seed.py --reset` to wipe and reseed.")
            return
        if reset:
            wipe(conn)
        seed(conn)
        conn.commit()
        print("Demo data loaded. See the login table in the chat for the accounts.")


if __name__ == "__main__":
    main()