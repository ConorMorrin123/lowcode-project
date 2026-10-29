import os
import secrets
from datetime import datetime, timezone
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template,
                   request, session, url_for)

import db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["DATABASE"] = os.path.join(app.root_path, "albumclub.db")
db.init_app(app)

PROPOSAL_SELECT = """
SELECT p.ProposalID, p.ClubID, p.Pitch, p.Status, p.WonAt,
       u.Name AS ProposerName,
       a.Title, a.Artist, a.Year, a.Genre,
       (SELECT COUNT(*) FROM Vote v WHERE v.ProposalID = p.ProposalID) AS Votes,
       (SELECT AVG(Rating) FROM Review r WHERE r.ProposalID = p.ProposalID) AS AvgRating,
       (SELECT COUNT(*) FROM Review r WHERE r.ProposalID = p.ProposalID) AS ReviewCount
FROM Proposal p
JOIN Album a ON a.AlbumID = p.AlbumID
JOIN User u ON u.UserID = p.ProposedBy
"""


# ---------------------------------------------------------------- helpers

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@app.before_request
def load_user():
    g.user = None
    user_id = session.get("user_id")
    if user_id is not None:
        g.user = db.get_db().execute(
            "SELECT * FROM User WHERE UserID = ?", (user_id,)).fetchone()
        if g.user is None:
            session.clear()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def require_member(club_id):
    """Return (club, membership). Non-members get a 404 so a club's
    existence and data are not revealed to outsiders."""
    conn = db.get_db()
    club = conn.execute("SELECT * FROM Club WHERE ClubID = ?", (club_id,)).fetchone()
    membership = conn.execute(
        "SELECT * FROM Membership WHERE ClubID = ? AND UserID = ?",
        (club_id, g.user["UserID"])).fetchone()
    if club is None or membership is None:
        abort(404)
    return club, membership


def require_admin(membership):
    if membership["Role"] != "admin":
        abort(403)


def get_proposal(proposal_id):
    proposal = db.get_db().execute(
        PROPOSAL_SELECT + " WHERE p.ProposalID = ?", (proposal_id,)).fetchone()
    if proposal is None:
        abort(404)
    return proposal


# ------------------------------------------------------------------- auth

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        errors = []
        if not name or len(name) > 200:
            errors.append("Name is required (max 200 characters).")
        if "@" not in email or len(email) < 3:
            errors.append("Please enter a valid email address.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("login.html", form=request.form)

        conn = db.get_db()
        user = conn.execute("SELECT * FROM User WHERE Email = ?", (email,)).fetchone()
        if user is None:
            cur = conn.execute("INSERT INTO User (Name, Email) VALUES (?, ?)", (name, email))
            conn.commit()
            user_id = cur.lastrowid
        else:
            user_id = user["UserID"]
        session.clear()
        session["user_id"] = user_id
        return redirect(url_for("home"))
    return render_template("login.html", form={})


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ------------------------------------------------------------------ clubs

@app.route("/")
@login_required
def home():
    clubs = db.get_db().execute(
        """SELECT c.ClubID, c.Name, m.Role
           FROM Membership m JOIN Club c ON c.ClubID = m.ClubID
           WHERE m.UserID = ? ORDER BY c.Name""",
        (g.user["UserID"],)).fetchall()
    return render_template("home.html", clubs=clubs)


@app.route("/club/new", methods=["GET", "POST"])
@login_required
def club_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name or len(name) > 200:
            flash("Club name is required (max 200 characters).", "error")
            return render_template("club_new.html", form=request.form)
        conn = db.get_db()
        while True:
            code = secrets.token_urlsafe(6)
            if conn.execute("SELECT 1 FROM Club WHERE JoinCode = ?", (code,)).fetchone() is None:
                break
        cur = conn.execute("INSERT INTO Club (Name, JoinCode) VALUES (?, ?)", (name, code))
        club_id = cur.lastrowid
        conn.execute(
            "INSERT INTO Membership (ClubID, UserID, Role, JoinedAt) VALUES (?, ?, 'admin', ?)",
            (club_id, g.user["UserID"], now()))
        conn.commit()
        return redirect(url_for("club_view", club_id=club_id))
    return render_template("club_new.html", form={})


@app.route("/club/join", methods=["GET", "POST"])
@login_required
def club_join():
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        conn = db.get_db()
        club = conn.execute("SELECT * FROM Club WHERE JoinCode = ?", (code,)).fetchone()
        if club is None:
            flash("That join code doesn't match any club.", "error")
            return render_template("club_join.html")
        already = conn.execute(
            "SELECT 1 FROM Membership WHERE ClubID = ? AND UserID = ?",
            (club["ClubID"], g.user["UserID"])).fetchone()
        if not already:
            conn.execute(
                "INSERT INTO Membership (ClubID, UserID, Role, JoinedAt) VALUES (?, ?, 'member', ?)",
                (club["ClubID"], g.user["UserID"], now()))
            conn.commit()
        return redirect(url_for("club_view", club_id=club["ClubID"]))
    return render_template("club_join.html")


@app.route("/club/<int:club_id>")
@login_required
def club_view(club_id):
    club, membership = require_member(club_id)
    conn = db.get_db()

    won = conn.execute(
        PROPOSAL_SELECT + " WHERE p.ClubID = ? AND p.Status = 'won' ORDER BY p.WonAt DESC",
        (club_id,)).fetchall()
    current = won[0] if won else None
    past = won[1:]

    pending = conn.execute(
        PROPOSAL_SELECT + " WHERE p.ClubID = ? AND p.Status = 'pending' ORDER BY p.ProposalID",
        (club_id,)).fetchall()
    approved = conn.execute(
        PROPOSAL_SELECT + " WHERE p.ClubID = ? AND p.Status = 'approved' ORDER BY p.ProposalID",
        (club_id,)).fetchall()

    my_vote = conn.execute(
        """SELECT v.ProposalID FROM Vote v
           JOIN Proposal p ON p.ProposalID = v.ProposalID
           WHERE v.UserID = ? AND p.ClubID = ? AND p.Status = 'approved'""",
        (g.user["UserID"], club_id)).fetchone()

    members = conn.execute(
        """SELECT u.Name, m.Role FROM Membership m JOIN User u ON u.UserID = m.UserID
           WHERE m.ClubID = ? ORDER BY m.Role, u.Name""", (club_id,)).fetchall()

    return render_template(
        "club.html", club=club, membership=membership, current=current, past=past,
        pending=pending, approved=approved,
        my_vote_id=my_vote["ProposalID"] if my_vote else None, members=members)


# -------------------------------------------------------------- proposals

@app.route("/club/<int:club_id>/propose", methods=["GET", "POST"])
@login_required
def propose(club_id):
    club, _ = require_member(club_id)
    if request.method == "GET":
        return render_template("propose.html", club=club, form={})

    title = request.form.get("title", "").strip()
    artist = request.form.get("artist", "").strip()
    genre = request.form.get("genre", "").strip()
    pitch = request.form.get("pitch", "").strip()
    year_raw = request.form.get("year", "").strip()

    errors = []
    if not title:
        errors.append("Album title is required.")
    if not artist:
        errors.append("Artist is required.")
    if not genre:
        errors.append("Genre is required.")
    try:
        year = int(year_raw)
        if not 1900 <= year <= datetime.now().year + 1:
            raise ValueError
    except ValueError:
        errors.append("Please enter a valid release year.")
        year = None
    if len(pitch) > 200:
        errors.append("Pitch must be 200 characters or fewer.")

    conn = db.get_db()
    album = None
    if not errors:
        album = conn.execute(
            "SELECT AlbumID FROM Album WHERE Title = ? AND Artist = ? AND Year = ?",
            (title, artist, year)).fetchone()
        if album:
            dup = conn.execute(
                """SELECT 1 FROM Proposal WHERE ClubID = ? AND AlbumID = ?
                   AND Status IN ('pending', 'approved', 'won')""",
                (club_id, album["AlbumID"])).fetchone()
            if dup:
                errors.append("This album has already been proposed or picked in this club.")

    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("propose.html", club=club, form=request.form)

    if album is None:
        cur = conn.execute(
            "INSERT INTO Album (Title, Artist, Year, Genre) VALUES (?, ?, ?, ?)",
            (title, artist, year, genre))
        album_id = cur.lastrowid
    else:
        album_id = album["AlbumID"]

    conn.execute(
        """INSERT INTO Proposal (ClubID, AlbumID, ProposedBy, Pitch, Status)
           VALUES (?, ?, ?, ?, 'pending')""",
        (club_id, album_id, g.user["UserID"], pitch or None))
    conn.commit()
    flash("Proposal submitted. An admin will review it.", "success")
    return redirect(url_for("club_view", club_id=club_id))


@app.route("/proposal/<int:proposal_id>")
@login_required
def proposal_view(proposal_id):
    proposal = get_proposal(proposal_id)
    club, _ = require_member(proposal["ClubID"])
    conn = db.get_db()
    reviews = conn.execute(
        """SELECT r.Rating, r.Comment, u.Name, r.UserID
           FROM Review r JOIN User u ON u.UserID = r.UserID
           WHERE r.ProposalID = ? ORDER BY r.ReviewID""", (proposal_id,)).fetchall()
    mine = next((r for r in reviews if r["UserID"] == g.user["UserID"]), None)
    return render_template("proposal.html", club=club, proposal=proposal,
                           reviews=reviews, mine=mine)


@app.route("/proposal/<int:proposal_id>/status", methods=["POST"])
@login_required
def proposal_status(proposal_id):
    proposal = get_proposal(proposal_id)
    _, membership = require_member(proposal["ClubID"])
    require_admin(membership)

    new_status = request.form.get("status")
    if new_status not in ("approved", "rejected"):
        abort(400)
    if proposal["Status"] != "pending":
        flash("Only pending proposals can be approved or rejected.", "error")
    else:
        conn = db.get_db()
        conn.execute("UPDATE Proposal SET Status = ? WHERE ProposalID = ?",
                     (new_status, proposal_id))
        conn.commit()
    return redirect(url_for("club_view", club_id=proposal["ClubID"]))


# ------------------------------------------------------------------ votes

@app.route("/proposal/<int:proposal_id>/vote", methods=["POST"])
@login_required
def vote(proposal_id):
    proposal = get_proposal(proposal_id)
    require_member(proposal["ClubID"])
    if proposal["Status"] != "approved":
        flash("You can only vote on approved proposals.", "error")
        return redirect(url_for("club_view", club_id=proposal["ClubID"]))

    conn = db.get_db()
    conn.execute(
        """DELETE FROM Vote WHERE UserID = ? AND ProposalID IN
           (SELECT ProposalID FROM Proposal WHERE ClubID = ? AND Status = 'approved')""",
        (g.user["UserID"], proposal["ClubID"]))
    conn.execute(
        "INSERT INTO Vote (ProposalID, UserID, ClubID, CastAt) VALUES (?, ?, ?, ?)",
        (proposal_id, g.user["UserID"], proposal["ClubID"], now()))
    conn.commit()
    flash("Vote recorded.", "success")
    return redirect(url_for("club_view", club_id=proposal["ClubID"]))


@app.route("/club/<int:club_id>/close-voting", methods=["POST"])
@login_required
def close_voting(club_id):
    _, membership = require_member(club_id)
    require_admin(membership)
    conn = db.get_db()
    top = conn.execute(
        """SELECT p.ProposalID, COUNT(v.VoteID) AS n
           FROM Proposal p LEFT JOIN Vote v ON v.ProposalID = p.ProposalID
           WHERE p.ClubID = ? AND p.Status = 'approved'
           GROUP BY p.ProposalID ORDER BY n DESC, p.ProposalID ASC LIMIT 1""",
        (club_id,)).fetchone()
    if top is None or top["n"] == 0:
        flash("There are no votes to close yet.", "error")
        return redirect(url_for("club_view", club_id=club_id))

    conn.execute("UPDATE Proposal SET Status = 'archived' WHERE ClubID = ? AND Status = 'approved'",
                 (club_id,))
    conn.execute("UPDATE Proposal SET Status = 'won', WonAt = ? WHERE ProposalID = ?",
                 (now(), top["ProposalID"]))
    conn.commit()
    flash("Voting closed. We have a new album of the week!", "success")
    return redirect(url_for("club_view", club_id=club_id))


# ---------------------------------------------------------------- reviews

@app.route("/proposal/<int:proposal_id>/review", methods=["POST"])
@login_required
def review(proposal_id):
    proposal = get_proposal(proposal_id)
    require_member(proposal["ClubID"])
    if proposal["Status"] != "won":
        abort(400)

    comment = request.form.get("comment", "").strip()
    try:
        rating = int(request.form.get("rating", ""))
        if not 1 <= rating <= 5:
            raise ValueError
    except ValueError:
        flash("Please choose a rating from 1 to 5.", "error")
        return redirect(url_for("proposal_view", proposal_id=proposal_id))
    if len(comment) > 1000:
        flash("Comments must be 1000 characters or fewer.", "error")
        return redirect(url_for("proposal_view", proposal_id=proposal_id))

    conn = db.get_db()
    conn.execute(
        """INSERT INTO Review (ProposalID, UserID, ClubID, Rating, Comment)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT (ProposalID, UserID)
           DO UPDATE SET Rating = excluded.Rating, Comment = excluded.Comment""",
        (proposal_id, g.user["UserID"], proposal["ClubID"], rating, comment or None))
    conn.commit()
    flash("Review saved.", "success")
    return redirect(url_for("proposal_view", proposal_id=proposal_id))


if __name__ == "__main__":
    app.run(debug=True)