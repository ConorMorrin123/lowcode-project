"""Band Finder: the Flask web app.

Run it from the lowcode-project folder (see the instructions at the bottom of
this file). All database work happens in db.py; this file only handles pages,
forms and who is allowed to do what.
"""
import os
import secrets
import sqlite3
from datetime import date, timedelta
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import db

HERE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(HERE, "static", "uploads")
PHOTO_TYPES = {".jpg", ".jpeg", ".png"}

app = Flask(__name__)
# The secret key comes from the environment, never from this file (see AGENTS.md).
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # photos up to 2 MB

# The same values the database CHECK rules allow (see schema/001_initial.sql).
SKILL_LEVELS = ("Beginner", "Intermediate", "Advanced", "Pro")
AGE_RANGES = ("18-24", "25-34", "35-44", "45-54", "55+")
COMMITMENTS = ("Casual", "Serious")
PROJECT_TYPES = ("Original band", "Covers band", "Wedding / function band",
                 "Jam only", "Session work")
AVAILABILITIES = ("Weeknights", "Weekends", "Weeknights and weekends", "Flexible")


# ---------------------------------------------------------------- helpers

@app.before_request
def load_user():
    """Look up the logged-in user (if any) before every page."""
    g.user = None
    user_id = session.get("user_id")
    if user_id is not None:
        g.user = db.get_user(user_id)
        if g.user is None:          # their account was deleted
            session.clear()


@app.context_processor
def page_helpers():
    """Values every template can use."""
    return {"is_admin": bool(g.user and g.user["is_admin"])}


@app.template_filter("day")
def day(timestamp):
    """'2026-11-28 17:30:00' -> '28 Nov 2026'."""
    if not timestamp:
        return ""
    return date.fromisoformat(timestamp[:10]).strftime("%d %b %Y").lstrip("0")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        if not g.user["is_admin"]:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def blank_to_none(value):
    value = (value or "").strip()
    return value or None


def to_int(value):
    """Turn form text into a whole number, or None if it isn't one."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_post_or_404(post_id):
    post = db.get_post(post_id)
    if post is None:
        abort(404)
    return post


def get_user_or_404(username):
    user = db.get_user_by_username(username)
    if user is None:
        abort(404)
    return user


def dropdowns():
    """Everything the forms need for their dropdown lists."""
    return {
        "counties": db.list_counties(),
        "instruments": db.list_instruments(),
        "genres": db.list_genres(),
        "skill_levels": SKILL_LEVELS,
        "age_ranges": AGE_RANGES,
        "commitments": COMMITMENTS,
        "project_types": PROJECT_TYPES,
        "availabilities": AVAILABILITIES,
    }


def with_tags(posts):
    """Add the wanted instruments and genres to each post for the post cards."""
    return [{"post": p,
             "instruments": db.list_post_instruments(p["id"]),
             "genres": db.list_post_genres(p["id"])} for p in posts]


# ----------------------------------------------------------- error pages

@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", code=404, title="Page not found",
                           message="We couldn't find that page."), 404


@app.errorhandler(403)
def forbidden(error):
    return render_template("error.html", code=403, title="Not allowed",
                           message="Only admins can see this page."), 403


@app.errorhandler(413)
def too_large(error):
    flash("That photo is too big. Please use a JPG or PNG under 2 MB.", "error")
    return redirect(url_for("edit_profile"))


# ------------------------------------------------------------------ home

@app.route("/")
def home():
    if g.user is None:
        return render_template("landing.html")
    return render_template(
        "home.html",
        suggested=with_tags(db.suggested_posts(g.user["id"])),
        newest=with_tags(db.list_open_posts()[:6]))


# --------------------------------------------------------------- account

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirmed_adult = 1 if request.form.get("confirmed_adult") == "yes" else 0

        errors = []
        if not 3 <= len(username) <= 30:
            errors.append("Username must be 3 to 30 characters.")
        if "@" not in email:
            errors.append("Please enter a valid email address.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if not confirmed_adult:
            errors.append("You must be 18 or over to join Band Finder.")
        if errors:
            for message in errors:
                flash(message, "error")
            return render_template("register.html", form=request.form)

        try:
            user_id = db.create_user(username, email, generate_password_hash(password),
                                     confirmed_adult)
        except sqlite3.IntegrityError:
            flash("That username or email is already taken.", "error")
            return render_template("register.html", form=request.form)

        session.clear()
        session["user_id"] = user_id
        flash("Welcome to Band Finder! Fill in your profile so people can find you.", "success")
        return redirect(url_for("edit_profile"))
    return render_template("register.html", form={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db.get_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Wrong email or password.", "error")
            return render_template("login.html", form=request.form)
        session.clear()
        session["user_id"] = user["id"]
        return redirect(url_for("home"))
    return render_template("login.html", form={})


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("home"))


# --------------------------------------------------------------- profile

@app.route("/user/<username>")
@login_required
def profile(username):
    user = get_user_or_404(username)
    county = next((c for c in db.list_counties() if c["id"] == user["county_id"]), None)
    own_posts = [p for p in db.list_open_posts() if p["user_id"] == user["id"]]
    return render_template(
        "profile.html", user=user, county=county,
        instruments=db.list_user_instruments(user["id"]),
        genres=db.list_user_genres(user["id"]),
        posts=with_tags(own_posts))


@app.route("/me/edit")
@login_required
def edit_profile():
    return render_template(
        "edit_profile.html", user=g.user,
        my_skills={row["id"]: row["skill_level"] for row in db.list_user_instruments(g.user["id"])},
        my_genres={row["id"] for row in db.list_user_genres(g.user["id"])},
        **dropdowns())


def save_photo(upload):
    """Save an uploaded photo with a random file name. Returns the name,
    or None if the file isn't a JPG or PNG."""
    extension = os.path.splitext(upload.filename)[1].lower()
    if extension not in PHOTO_TYPES:
        return None
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    name = secrets.token_hex(12) + extension
    upload.save(os.path.join(UPLOAD_FOLDER, name))
    return name


def delete_photo(name):
    if name:
        path = os.path.join(UPLOAD_FOLDER, os.path.basename(name))
        if os.path.exists(path):
            os.remove(path)


@app.route("/me", methods=["POST"])
@login_required
def save_profile():
    form = request.form
    user_id = g.user["id"]
    old_photo = g.user["photo_path"]
    photo = old_photo
    new_photo = None

    years_text = blank_to_none(form.get("years_playing"))
    years_playing = to_int(years_text)
    if years_text is not None and years_playing is None:
        flash("Years playing must be a whole number.", "error")
        return redirect(url_for("edit_profile"))

    upload = request.files.get("photo")
    if upload and upload.filename:
        new_photo = save_photo(upload)
        if new_photo is None:
            flash("Photos must be JPG or PNG.", "error")
            return redirect(url_for("edit_profile"))
        photo = new_photo
    elif form.get("remove_photo") == "yes":
        photo = None

    try:
        db.update_profile(
            user_id,
            display_name=blank_to_none(form.get("display_name")),
            photo_path=photo,
            bio=blank_to_none(form.get("bio")),
            age_range=blank_to_none(form.get("age_range")),
            years_playing=years_playing,
            influences=blank_to_none(form.get("influences")),
            gear=blank_to_none(form.get("gear")),
            county_id=to_int(form.get("county_id")),
            commitment=blank_to_none(form.get("commitment")),
            project_type=blank_to_none(form.get("project_type")),
            availability=blank_to_none(form.get("availability")),
            soundcloud_url=blank_to_none(form.get("soundcloud_url")),
            youtube_url=blank_to_none(form.get("youtube_url")),
            spotify_url=blank_to_none(form.get("spotify_url")),
            instagram_url=blank_to_none(form.get("instagram_url")),
            public_email=blank_to_none(form.get("public_email")),
            public_phone=blank_to_none(form.get("public_phone")),
        )
        skills = []
        for instrument in db.list_instruments():
            level = form.get("skill_" + str(instrument["id"]))
            if level in SKILL_LEVELS:
                skills.append((instrument["id"], level))
        db.set_user_instruments(user_id, skills)
        db.set_user_genres(user_id, [to_int(v) for v in form.getlist("genre_ids") if to_int(v)])
    except sqlite3.IntegrityError:
        delete_photo(new_photo)
        flash("Some of those details weren't allowed. Check that links start with https://, "
              "and that bio, influences and gear are under 500 characters.", "error")
        return redirect(url_for("edit_profile"))

    if photo != old_photo:
        delete_photo(old_photo)
    flash("Profile saved.", "success")
    return redirect(url_for("profile", username=g.user["username"]))


# ------------------------------------------------------------------ posts

@app.route("/posts")
@login_required
def posts():
    filters = {
        "instrument_id": to_int(request.args.get("instrument")),
        "genre_id": to_int(request.args.get("genre")),
        "county_id": to_int(request.args.get("county")),
        "skill_level": request.args.get("skill") if request.args.get("skill") in SKILL_LEVELS else None,
        "commitment": request.args.get("commitment") if request.args.get("commitment") in COMMITMENTS else None,
    }
    return render_template(
        "posts.html",
        posts=with_tags(db.list_open_posts(**filters)),
        suggested=with_tags(db.suggested_posts(g.user["id"])),
        filters=filters, filtering=any(v is not None for v in filters.values()),
        **dropdowns())


@app.route("/posts/new")
@login_required
def new_post():
    return render_template("post_new.html", form={}, today=date.today().isoformat(),
                           last_day=(date.today() + timedelta(days=30)).isoformat(), **dropdowns())


@app.route("/posts", methods=["POST"])
@login_required
def create_post():
    form = request.form
    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    county_id = to_int(form.get("county_id"))
    commitment = form.get("commitment")
    instrument_ids = [to_int(v) for v in form.getlist("instrument_ids") if to_int(v)]
    genre_ids = [to_int(v) for v in form.getlist("genre_ids") if to_int(v)]

    errors = []
    if not 1 <= len(title) <= 100:
        errors.append("Give your post a title (up to 100 characters).")
    if not 1 <= len(description) <= 2000:
        errors.append("Add a description (up to 2000 characters).")
    if county_id is None:
        errors.append("Choose a county.")
    if commitment not in COMMITMENTS:
        errors.append("Choose Casual or Serious.")
    if not instrument_ids:
        errors.append("Choose at least one instrument you are looking for.")

    # Optional expiry date. Posts last 30 days at most (that is also the default).
    expires_at = None
    chosen = blank_to_none(form.get("expires_on"))
    if chosen:
        try:
            chosen_day = date.fromisoformat(chosen)
        except ValueError:
            chosen_day = None
        if chosen_day is None or chosen_day <= date.today():
            errors.append("The expiry date must be after today.")
        elif chosen_day > date.today() + timedelta(days=30):
            errors.append("Posts can last 30 days at most.")
        elif chosen_day < date.today() + timedelta(days=30):
            expires_at = chosen + " 23:59:59"
        # Choosing exactly 30 days from today uses the default (30 days from now).

    if errors:
        for message in errors:
            flash(message, "error")
        return render_template("post_new.html", form=form, today=date.today().isoformat(),
                               last_day=(date.today() + timedelta(days=30)).isoformat(),
                               **dropdowns()), 400
    try:
        post_id = db.create_post(g.user["id"], title, description, county_id, commitment,
                                 instrument_ids, genre_ids, expires_at)
    except sqlite3.IntegrityError:
        flash("That post couldn't be saved. Please check the county, instruments and genres.", "error")
        return render_template("post_new.html", form=form, today=date.today().isoformat(),
                               last_day=(date.today() + timedelta(days=30)).isoformat(),
                               **dropdowns()), 400
    flash("Your post is live for up to 30 days.", "success")
    return redirect(url_for("post_detail", post_id=post_id))


@app.route("/posts/<int:post_id>")
@login_required
def post_detail(post_id):
    post = get_post_or_404(post_id)
    return render_template(
        "post.html", post=post,
        instruments=db.list_post_instruments(post_id),
        genres=db.list_post_genres(post_id),
        comments=db.list_comments(post_id),
        expired=post["expires_at"] <= db.now())


@app.route("/posts/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = get_post_or_404(post_id)
    if post["user_id"] != g.user["id"]:
        abort(403)
    db.delete_post(post_id)
    flash("Post deleted.", "success")
    return redirect(url_for("posts"))


# --------------------------------------------------------------- comments

@app.route("/posts/<int:post_id>/comments", methods=["POST"])
@login_required
def add_comment(post_id):
    get_post_or_404(post_id)
    body = request.form.get("body", "").strip()
    if not 1 <= len(body) <= 1000:
        flash("Comments must be 1 to 1000 characters.", "error")
        return redirect(url_for("post_detail", post_id=post_id))
    try:
        db.create_comment(post_id, g.user["id"], body)
    except sqlite3.IntegrityError:
        flash("That comment couldn't be saved.", "error")
    return redirect(url_for("post_detail", post_id=post_id) + "#comments")


@app.route("/comments/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = db.get_comment(comment_id)
    if comment is None:
        abort(404)
    if comment["user_id"] != g.user["id"]:
        abort(403)
    db.delete_comment(comment_id)
    flash("Comment deleted.", "success")
    return redirect(url_for("post_detail", post_id=comment["post_id"]) + "#comments")


# ---------------------------------------------------------------- reports

@app.route("/user/<username>/report", methods=["GET", "POST"])
@login_required
def report_user(username):
    user = get_user_or_404(username)
    if user["id"] == g.user["id"]:
        flash("You can't report yourself.", "error")
        return redirect(url_for("profile", username=username))
    if request.method == "POST":
        reason = request.form.get("reason", "").strip()
        if not 1 <= len(reason) <= 1000:
            flash("Please tell us what happened (up to 1000 characters).", "error")
            return render_template("report.html", user=user, form=request.form), 400
        try:
            db.create_report(g.user["id"], user["id"], reason)
        except sqlite3.IntegrityError:
            flash("That report couldn't be saved.", "error")
            return render_template("report.html", user=user, form=request.form), 400
        flash("Thanks. An admin will look at your report.", "success")
        return redirect(url_for("profile", username=username))
    return render_template("report.html", user=user, form={})


# ------------------------------------------------------------------ admin

@app.route("/admin")
@admin_required
def admin():
    return render_template("admin.html", reports=db.list_open_reports(), users=db.list_users())


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    user = db.get_user(user_id)
    if user is None:
        abort(404)
    if user_id == g.user["id"]:
        flash("You can't delete your own account from the admin page.", "error")
        return redirect(url_for("admin"))
    delete_photo(user["photo_path"])
    db.delete_user(user_id)
    flash(user["username"] + " was deleted. Their posts and comments now show 'Deleted user'.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/users/<int:user_id>/make-admin", methods=["POST"])
@admin_required
def admin_make_admin(user_id):
    user = db.get_user(user_id)
    if user is None:
        abort(404)
    db.make_admin(user_id)
    flash(user["username"] + " is now an admin.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/reports/<int:report_id>/resolve", methods=["POST"])
@admin_required
def admin_resolve_report(report_id):
    db.resolve_report(report_id)
    flash("Report marked as resolved.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/posts/<int:post_id>/delete", methods=["POST"])
@admin_required
def admin_delete_post(post_id):
    get_post_or_404(post_id)
    db.delete_post(post_id)
    flash("Post deleted by admin.", "success")
    return redirect(url_for("posts"))


@app.route("/admin/comments/<int:comment_id>/remove", methods=["POST"])
@admin_required
def admin_remove_comment(comment_id):
    comment = db.get_comment(comment_id)
    if comment is None:
        abort(404)
    db.remove_comment_by_admin(comment_id)
    flash("Comment removed. It now shows 'Removed by admin'.", "success")
    return redirect(url_for("post_detail", post_id=comment["post_id"]) + "#comments")


# How to run (from the lowcode-project folder, in PowerShell):
#   python tools/migrate.py bandfinder/app.db --schema bandfinder/schema
#   $env:SECRET_KEY = "any-long-random-text"
#   .venv\Scripts\python.exe -m flask --app bandfinder/app.py run --debug
if __name__ == "__main__":
    app.run(debug=True)
