"""Tests for the Band Finder web pages, using Flask's test client.

Each test gets a brand-new temporary database, never the real bandfinder/app.db.

Run from the lowcode-project folder:
    .venv\\Scripts\\python.exe -m unittest discover -s bandfinder/tests -v
"""
import io
import os
import sys
import unittest

BANDFINDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BANDFINDER)

# A throwaway key just for tests. The real key always comes from the environment.
os.environ.setdefault("SECRET_KEY", "test-only-not-a-real-secret")

from test_constraints import DatabaseTestCase  # noqa: E402  (temp database set-up)

import db       # noqa: E402
import app as app_module  # noqa: E402
from app import app  # noqa: E402


class AppTestCase(DatabaseTestCase):

    def setUp(self):
        super().setUp()
        app.config["TESTING"] = True
        self.client = app.test_client()

    def sign_up(self, username="aoife", password="password123"):
        return self.client.post("/register", data={
            "username": username, "email": username + "@example.com",
            "password": password, "confirmed_adult": "yes"})

    def log_in_as_new_user(self, username="aoife"):
        self.sign_up(username)
        return db.get_user_by_username(username)["id"]

    def log_out(self):
        self.client.post("/logout")


class TestPagesLoad(AppTestCase):

    def test_landing_page_for_visitors(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Find your next band mate", page.data)

    def test_pages_need_login(self):
        for path in ("/posts", "/posts/new", "/me/edit"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 302)

    def test_every_member_page_loads(self):
        self.log_in_as_new_user()
        for path in ("/", "/posts", "/posts/new", "/me/edit", "/user/aoife"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)


class TestNotFound(AppTestCase):

    def test_missing_post_is_404(self):
        self.log_in_as_new_user()
        self.assertEqual(self.client.get("/posts/999").status_code, 404)

    def test_missing_user_is_404(self):
        self.log_in_as_new_user()
        self.assertEqual(self.client.get("/user/nobody").status_code, 404)

    def test_unknown_page_is_404(self):
        self.assertEqual(self.client.get("/no-such-page").status_code, 404)


class TestSignUp(AppTestCase):

    def test_sign_up_and_log_in(self):
        self.assertEqual(self.sign_up().status_code, 302)
        self.log_out()
        page = self.client.post("/login", data={"email": "aoife@example.com",
                                                "password": "password123"})
        self.assertEqual(page.status_code, 302)

    def test_duplicate_username_shows_friendly_message(self):
        self.sign_up("aoife")
        self.log_out()
        page = self.client.post("/register", data={
            "username": "aoife", "email": "other@example.com",
            "password": "password123", "confirmed_adult": "yes"})
        self.assertEqual(page.status_code, 200)          # stays on the form, no crash
        self.assertIn(b"already taken", page.data)

    def test_must_tick_18_or_over(self):
        page = self.client.post("/register", data={
            "username": "young", "email": "young@example.com", "password": "password123"})
        self.assertIn(b"18 or over", page.data)
        self.assertIsNone(db.get_user_by_username("young"))

    def test_wrong_password_is_refused(self):
        self.sign_up()
        self.log_out()
        page = self.client.post("/login", data={"email": "aoife@example.com", "password": "nope"})
        self.assertIn(b"Wrong email or password", page.data)


class TestReviewFixes(AppTestCase):
    """Week 3 review fixes (docs2/week03-review.md)."""

    def setUp(self):
        super().setUp()
        # Save test photos in the temp folder, never in bandfinder/static/uploads.
        self.old_upload_folder = app_module.UPLOAD_FOLDER
        app_module.UPLOAD_FOLDER = os.path.join(self.folder, "uploads")

    def tearDown(self):
        app_module.UPLOAD_FOLDER = self.old_upload_folder
        super().tearDown()

    def test_username_with_slash_is_refused_with_a_message(self):
        page = self.sign_up("a/b")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"only letters", page.data)
        self.assertIsNone(db.get_user_by_username("a/b"))

    def test_username_differing_only_in_capitals_is_refused(self):
        self.sign_up("Aoife")
        self.log_out()
        page = self.sign_up("aoife")
        self.assertIn(b"already taken", page.data)
        self.assertIsNone(db.get_user_by_username("aoife"))

    def upload(self, filename, content):
        return self.client.post("/me", data={"photo": (io.BytesIO(content), filename)},
                                content_type="multipart/form-data", follow_redirects=True)

    def test_fake_photo_is_refused(self):
        self.log_in_as_new_user()
        page = self.upload("evil.png", b"<html><script>alert(1)</script></html>")
        self.assertIn(b"real JPG or PNG", page.data)
        self.assertIsNone(db.get_user_by_username("aoife")["photo_path"])

    def test_real_png_is_accepted(self):
        self.log_in_as_new_user()
        self.upload("me.png", app_module.PNG_START + b"rest of the image")
        photo = db.get_user_by_username("aoife")["photo_path"]
        self.assertTrue(photo.endswith(".png"))
        self.assertTrue(os.path.exists(os.path.join(app_module.UPLOAD_FOLDER, photo)))

    def test_jpeg_named_png_is_saved_as_jpg(self):
        self.log_in_as_new_user()
        self.upload("me.png", app_module.JPEG_START + b"rest of the image")
        self.assertTrue(db.get_user_by_username("aoife")["photo_path"].endswith(".jpg"))

    def test_login_blocked_after_five_wrong_passwords(self):
        self.sign_up("aoife")
        self.log_out()
        for _ in range(5):
            self.client.post("/login", data={"email": "aoife@example.com", "password": "wrong"})
        # Even the right password is refused until the 15 minutes are up.
        page = self.client.post("/login", data={"email": "aoife@example.com",
                                                "password": "password123"})
        self.assertEqual(page.status_code, 429)
        self.assertIn(b"Too many wrong attempts", page.data)

    def test_successful_login_clears_wrong_attempts(self):
        self.sign_up("aoife")
        self.log_out()
        for _ in range(4):
            self.client.post("/login", data={"email": "aoife@example.com", "password": "wrong"})
        self.client.post("/login", data={"email": "aoife@example.com", "password": "password123"})
        self.assertEqual(db.count_recent_failed_logins("aoife@example.com"), 0)


class TestProfile(AppTestCase):

    def test_save_profile_with_instruments_and_genres(self):
        user = self.log_in_as_new_user()
        drums = self.instrument("Drums")
        page = self.client.post("/me", data={
            "display_name": "Aoife B", "county_id": str(self.county("Galway")),
            "skill_" + str(drums): "Advanced", "genre_ids": [str(self.genre("Rock"))],
            "spotify_url": "https://open.spotify.com/artist/1", "years_playing": "6"})
        self.assertEqual(page.status_code, 302)
        self.assertEqual([r["skill_level"] for r in db.list_user_instruments(user)], ["Advanced"])
        profile = self.client.get("/user/aoife")
        self.assertIn(b"Aoife B", profile.data)
        self.assertIn(b"Galway", profile.data)

    def test_bad_link_shows_friendly_message(self):
        self.log_in_as_new_user()
        page = self.client.post("/me", data={"spotify_url": "http://not-secure"},
                                follow_redirects=True)
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"https://", page.data)
        self.assertIsNone(db.get_user_by_username("aoife")["spotify_url"])


class TestPosts(AppTestCase):

    def post_form(self, **changes):
        data = {"title": "Bassist wanted", "description": "Funk band, weekly rehearsals.",
                "county_id": str(self.county("Dublin")), "commitment": "Casual",
                "instrument_ids": [str(self.instrument("Bass"))]}
        data.update(changes)
        return data

    def test_create_and_view_post(self):
        self.log_in_as_new_user()
        page = self.client.post("/posts", data=self.post_form())
        self.assertEqual(page.status_code, 302)
        listing = self.client.get("/posts")
        self.assertIn(b"Bassist wanted", listing.data)

    def test_missing_title_stays_on_form(self):
        self.log_in_as_new_user()
        page = self.client.post("/posts", data=self.post_form(title=""))
        self.assertEqual(page.status_code, 400)
        self.assertIn(b"Give your post a title", page.data)
        self.assertEqual(self.count("post"), 0)

    def test_expiry_over_30_days_is_refused(self):
        self.log_in_as_new_user()
        page = self.client.post("/posts", data=self.post_form(expires_on="2099-01-01"))
        self.assertIn(b"30 days at most", page.data)
        self.assertEqual(self.count("post"), 0)

    def test_filter_by_county(self):
        self.log_in_as_new_user()
        self.client.post("/posts", data=self.post_form(title="Dublin post"))
        self.client.post("/posts", data=self.post_form(title="Cork post",
                                                       county_id=str(self.county("Cork"))))
        page = self.client.get("/posts?county=" + str(self.county("Cork")))
        self.assertIn(b"Cork post", page.data)
        self.assertNotIn(b"Dublin post", page.data)

    def test_only_the_author_can_delete_a_post(self):
        author = self.log_in_as_new_user("aoife")
        post = self.make_post(author)
        self.log_out()
        self.log_in_as_new_user("brian")
        self.assertEqual(self.client.post("/posts/" + str(post) + "/delete").status_code, 403)
        self.assertIsNotNone(db.get_post(post))

    def test_comment_and_deleted_user(self):
        author = self.make_user("aoife")
        post = self.make_post(author)
        self.log_in_as_new_user("brian")
        self.client.post("/posts/" + str(post) + "/comments", data={"body": "I can play!"})
        db.delete_user(author)
        page = self.client.get("/posts/" + str(post))
        self.assertIn(b"I can play!", page.data)
        self.assertIn(b"Deleted user", page.data)


class TestAdmin(AppTestCase):

    def test_members_get_403_on_admin_pages(self):
        self.log_in_as_new_user()
        self.assertEqual(self.client.get("/admin").status_code, 403)

    def test_admin_removes_comment(self):
        author = self.make_user("brian")
        post = self.make_post(author)
        comment = db.create_comment(post, author, "Something rude")
        admin = self.log_in_as_new_user("admin")
        db.make_admin(admin)
        self.client.post("/admin/comments/" + str(comment) + "/remove")
        self.log_out()
        self.log_in_as_new_user("ciara")
        page = self.client.get("/posts/" + str(post))
        self.assertIn(b"Removed by admin", page.data)
        self.assertNotIn(b"Something rude", page.data)   # hidden from normal users

    def test_admin_deletes_user_and_resolves_report(self):
        bad = self.make_user("brian")
        reporter = self.make_user("ciara")
        report = db.create_report(reporter, bad, "Spam")
        admin = self.log_in_as_new_user("admin")
        db.make_admin(admin)
        self.assertEqual(self.client.get("/admin").status_code, 200)
        self.client.post("/admin/users/" + str(bad) + "/delete")
        self.assertIsNone(db.get_user(bad))
        self.client.post("/admin/reports/" + str(report) + "/resolve")
        self.assertEqual(db.list_open_reports(), [])


class TestReport(AppTestCase):

    def test_report_a_user(self):
        self.make_user("brian")
        self.log_in_as_new_user("aoife")
        page = self.client.post("/user/brian/report", data={"reason": "Spam posts"})
        self.assertEqual(page.status_code, 302)
        self.assertEqual(self.count("report"), 1)

    def test_cannot_report_yourself(self):
        self.log_in_as_new_user("aoife")
        self.client.post("/user/aoife/report", data={"reason": "Me"})
        self.assertEqual(self.count("report"), 0)


if __name__ == "__main__":
    unittest.main()
