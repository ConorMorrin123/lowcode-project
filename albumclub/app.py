import os
import secrets
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import db

app = Flask(__name__)
# The secret key comes from the environment, never from this file (see AGENTS.md).
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

PRIVACY_SETTINGS = ("open", "invite_only")


# ---------------------------------------------------------------- helpers

@app.before_request
def load_user():
    g.user = None
    user_id = session.get("user_id")
    if user_id is not None:
        g.user = db.get_user(user_id)
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
    """Return (club, membership). Anyone who is not an active member gets a
    404, so a club's existence and data are not revealed to outsiders."""
    club = db.get_club(club_id)
    membership = db.get_membership(club_id, g.user["id"])
    if club is None or membership is None or membership["status"] != "active":
        abort(404)
    return club, membership


def require_admin(membership):
    if membership["role"] != "admin":
        abort(403)


def get_proposal_or_404(proposal_id):
    proposal = db.get_proposal(proposal_id)
    if proposal is None:
        abort(404)
    return proposal


def this_week(club):
    return db.current_week_start(club["changeover_day"])


def blank_to_none(value):
    value = value.strip()
    return value or None


# ------------------------------------------------------------------- auth

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        music_taste = blank_to_none(request.form.get("music_taste", ""))

        errors = []
        if not username or len(username) > 50:
            errors.append("Username is required (max 50 characters).")
        if "@" not in email or len(email) < 3:
            errors.append("Please enter a valid email address.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", form=request.form)

        try:
            user_id = db.create_user(username, email, generate_password_hash(password), music_taste)
        except sqlite3.IntegrityError:
            flash("That username or email is already taken.", "error")
            return render_template("register.html", form=request.form)

        session.clear()
        session["user_id"] = user_id
        return redirect(url_for("home"))
    return render_template("register.html", form={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db.get_user_by_username(username)
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Wrong username or password.", "error")
            return render_template("login.html", form=request.form)
        session.clear()
        session["user_id"] = user["id"]
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
    clubs = db.list_clubs_for_user(g.user["id"])
    return render_template("home.html", clubs=clubs)


@app.route("/club/new", methods=["GET", "POST"])
@login_required
def club_new():
    if request.method == "GET":
        return render_template("club_new.html", form={}, days=db.DAYS)

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    privacy_setting = request.form.get("privacy_setting", "")
    changeover_day = request.form.get("changeover_day", "")

    errors = []
    if not name or len(name) > 200:
        errors.append("Club name is required (max 200 characters).")
    if not description or len(description) > 500:
        errors.append("A short description is required (max 500 characters).")
    if privacy_setting not in PRIVACY_SETTINGS:
        errors.append("Please choose who can join.")
    if changeover_day not in db.DAYS:
        errors.append("Please choose a changeover day.")
    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("club_new.html", form=request.form, days=db.DAYS)

    # A random invite code. The database's UNIQUE rule guarantees no repeats.
    invite_code = secrets.token_urlsafe(6)
    try:
        club_id = db.create_club(name, description, invite_code,
                                 privacy_setting, changeover_day, g.user["id"])
    except sqlite3.IntegrityError:
        flash("A club with that name already exists. Please pick another name.", "error")
        return render_template("club_new.html", form=request.form, days=db.DAYS)
    return redirect(url_for("club_view", club_id=club_id))


@app.route("/club/join", methods=["GET", "POST"])
@login_required
def club_join():
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        club = db.get_club_by_invite_code(code)
        if club is None:
            flash("That invite code doesn't match any club.", "error")
            return render_template("club_join.html")

        membership = db.get_membership(club["id"], g.user["id"])
        try:
            if membership is None:
                db.create_membership(g.user["id"], club["id"], "member", "active")
            elif membership["status"] != "active":
                # Someone who left (or was pending) is welcomed back.
                db.update_membership(membership["id"], membership["role"], "active")
        except sqlite3.IntegrityError:
            flash("Sorry, we couldn't add you to that club.", "error")
            return render_template("club_join.html")
        return redirect(url_for("club_view", club_id=club["id"]))
    return render_template("club_join.html")


@app.route("/club/<int:club_id>")
@login_required
def club_view(club_id):
    club, membership = require_member(club_id)
    week = this_week(club)

    winners = db.list_winners(club_id)
    current = winners[0] if winners else None
    past = winners[1:]

    my_vote = db.get_vote(club_id, g.user["id"], week)

    return render_template(
        "club.html", club=club, membership=membership, week=week,
        current=current, past=past,
        pending=db.list_proposals(club_id, "pending"),
        approved=db.list_approved_with_votes(club_id, week),
        my_vote_id=my_vote["proposal_id"] if my_vote else None,
        voting_closed=db.winner_exists_for_week(club_id, week),
        members=db.list_members(club_id))


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
    year_raw = request.form.get("release_year", "").strip()
    cover_art_url = blank_to_none(request.form.get("cover_art_url", ""))
    listening_url = blank_to_none(request.form.get("listening_url", ""))

    errors = []
    if not title:
        errors.append("Album title is required.")
    if not artist:
        errors.append("Artist is required.")
    if not genre:
        errors.append("Genre is required.")
    release_year = None
    if year_raw:
        try:
            release_year = int(year_raw)
            if not 1900 <= release_year <= datetime.now().year + 1:
                raise ValueError
        except ValueError:
            errors.append("Please enter a valid release year, or leave it blank.")

    album = None
    if not errors:
        album = db.find_album(club_id, title, artist)
        if album is not None and db.album_has_open_proposal(album["id"]):
            errors.append("This album has already been proposed or picked in this club.")

    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("propose.html", club=club, form=request.form)

    try:
        db.propose_album(club_id, g.user["id"], this_week(club),
                         album["id"] if album else None,
                         title, artist, genre, release_year, cover_art_url, listening_url)
    except sqlite3.IntegrityError:
        flash("Sorry, that proposal couldn't be saved. Please check the details.", "error")
        return render_template("propose.html", club=club, form=request.form)

    flash("Proposal submitted. An admin will review it.", "success")
    return redirect(url_for("club_view", club_id=club_id))


@app.route("/proposal/<int:proposal_id>")
@login_required
def proposal_view(proposal_id):
    proposal = get_proposal_or_404(proposal_id)
    club, _ = require_member(proposal["club_id"])
    reviews = db.list_reviews(proposal["album_id"])
    mine = db.get_user_review(proposal["album_id"], g.user["id"])
    return render_template("proposal.html", club=club, proposal=proposal,
                           reviews=reviews, mine=mine,
                           can_review=db.album_is_reviewable(proposal["album_id"]))


@app.route("/proposal/<int:proposal_id>/status", methods=["POST"])
@login_required
def proposal_status(proposal_id):
    proposal = get_proposal_or_404(proposal_id)
    _, membership = require_member(proposal["club_id"])
    require_admin(membership)

    new_status = request.form.get("status")
    if new_status not in ("approved", "rejected"):
        abort(400)
    if proposal["status"] != "pending":
        flash("Only pending proposals can be approved or rejected.", "error")
    else:
        db.update_proposal_status(proposal_id, new_status, g.user["id"])
    return redirect(url_for("club_view", club_id=proposal["club_id"]))


# ------------------------------------------------------------------ votes

@app.route("/proposal/<int:proposal_id>/vote", methods=["POST"])
@login_required
def vote(proposal_id):
    proposal = get_proposal_or_404(proposal_id)
    club, _ = require_member(proposal["club_id"])
    back = redirect(url_for("club_view", club_id=club["id"]))
    if proposal["status"] != "approved":
        flash("You can only vote on approved proposals.", "error")
        return back

    week = this_week(club)
    if db.winner_exists_for_week(club["id"], week):
        flash("Voting is closed for this week.", "error")
        return back

    existing = db.get_vote(club["id"], g.user["id"], week)
    try:
        if existing is None:
            db.create_vote(club["id"], proposal_id, g.user["id"], week)
        else:
            db.update_vote(existing["id"], proposal_id)
    except sqlite3.IntegrityError:
        flash("Sorry, your vote couldn't be saved.", "error")
        return back
    flash("Vote recorded.", "success")
    return back


@app.route("/club/<int:club_id>/close-voting", methods=["POST"])
@login_required
def close_voting(club_id):
    club, membership = require_member(club_id)
    require_admin(membership)
    week = this_week(club)
    if db.winner_exists_for_week(club_id, week):
        flash("This week's album has already been picked.", "error")
    elif db.pick_winner(club_id, week) is None:
        flash("There are no votes to close yet.", "error")
    else:
        flash("Voting closed. We have a new album of the week!", "success")
    return redirect(url_for("club_view", club_id=club_id))


# ---------------------------------------------------------------- reviews

@app.route("/proposal/<int:proposal_id>/review", methods=["POST"])
@login_required
def review(proposal_id):
    proposal = get_proposal_or_404(proposal_id)
    require_member(proposal["club_id"])
    if not db.album_is_reviewable(proposal["album_id"]):
        abort(400)

    back = redirect(url_for("proposal_view", proposal_id=proposal_id))
    review_text = request.form.get("review_text", "").strip()
    try:
        rating = int(request.form.get("rating", ""))
        if not 1 <= rating <= 5:
            raise ValueError
    except ValueError:
        flash("Please choose a rating from 1 to 5.", "error")
        return back
    if not review_text or len(review_text) > 1000:
        flash("Please write a review (max 1000 characters).", "error")
        return back

    mine = db.get_user_review(proposal["album_id"], g.user["id"])
    try:
        if mine is None:
            db.create_review(proposal["album_id"], g.user["id"], rating, review_text)
        else:
            db.update_review(mine["id"], rating, review_text)
    except sqlite3.IntegrityError:
        flash("Sorry, your review couldn't be saved.", "error")
        return back
    flash("Review saved.", "success")
    return back


if __name__ == "__main__":
    app.run(debug=True)
