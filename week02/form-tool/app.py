import re
from flask import Flask, render_template, request

# Initialize the Flask web application
app = Flask(__name__)

# Regular Expression (Regex) pattern for server-side email validation.
# Format explanation:
#   ^[^\s@]+  -> Must start with 1+ characters that are NOT whitespace or '@'
#   @         -> Followed by an '@' symbol
#   [^\s@]+   -> Followed by 1+ domain characters (NOT whitespace or '@')
#   \.        -> Followed by a dot '.'
#   [^\s@]+$  -> Ends with 1+ top-level domain characters (NOT whitespace or '@')
EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@app.route("/", methods=["GET"])
def index():
    """
    Route: GET /
    Renders the initial empty contact form page.
    Passes empty dicts for 'errors' and 'form_data' so Jinja templates don't throw undefined errors.
    """
    return render_template("form.html", errors={}, form_data={})


@app.route("/contact", methods=["POST"])
def contact():
    """
    Route: POST /contact
    Handles form submission:
      1. Extracts inputs sent via request.form
      2. Validates name, email, and message fields
      3. Re-renders form with errors if validation fails
      4. Renders confirmation page if validation succeeds
    """
    # Safely extract user input values from the HTML form (defaults to empty string if key missing)
    name = request.form.get("name", "")
    email = request.form.get("email", "")
    message = request.form.get("message", "")

    # Dictionary to hold field-specific error messages
    errors = {}

    # ----------------------------------------------------
    # 1. NAME VALIDATION
    # ----------------------------------------------------
    # .strip() removes leading and trailing spaces.
    # If a user enters "   ", not name.strip() evaluates to True and catches whitespace-only input.
    if not name or not name.strip():
        errors["name"] = "Name cannot be empty or consist only of spaces."

    # ----------------------------------------------------
    # 2. EMAIL VALIDATION
    # ----------------------------------------------------
    if not email or not email.strip():
        errors["email"] = "Email address is required."
    elif not EMAIL_REGEX.match(email.strip()):
        errors["email"] = "Please enter a valid email address (e.g., user@example.com)."

    # ----------------------------------------------------
    # 3. MESSAGE VALIDATION
    # ----------------------------------------------------
    if not message or not message.strip():
        errors["message"] = "Message cannot be empty or consist only of spaces."

    # ----------------------------------------------------
    # 4. HANDLE VALIDATION ERRORS
    # ----------------------------------------------------
    # If the errors dictionary contains any key-value pairs, validation failed.
    if errors:
        # Re-render form with error messages and return HTTP status 400 (Bad Request).
        # We pass back 'form_data' so the fields stay filled with what the user previously typed ("sticky inputs").
        return render_template(
            "form.html",
            errors=errors,
            form_data={"name": name, "email": email, "message": message}
        ), 400

    # ----------------------------------------------------
    # 5. HANDLE SUCCESSFUL SUBMISSION
    # ----------------------------------------------------
    # Clean the input data by removing surrounding extra whitespace
    sanitized_data = {
        "name": name.strip(),
        "email": email.strip(),
        "message": message.strip()
    }

    # Display the confirmation view with the clean submitted data
    return render_template("confirmation.html", data=sanitized_data)


# Standard Python boiler-plate: runs dev server when executing 'python app.py' directly
if __name__ == "__main__":
    app.run(debug=True)