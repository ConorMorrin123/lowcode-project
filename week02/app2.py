import os
from flask import Flask, render_template, request, flash, redirect, url_for

app = Flask(__name__)
# Secret key required for session management and flash messages
app.secret_key = os.urandom(24)

@app.route("/", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        # Basic form validation
        if not name or not email or not message:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("contact"))

        # Form submission processing logic (e.g., database storage, email sending)
        flash(f"Thank you, {name}! Your message has been sent.", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html")

if __name__ == "__main__":
    app.run(debug=True)