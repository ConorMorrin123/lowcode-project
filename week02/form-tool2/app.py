"""
Contact form app (Flask)
========================

What it does
------------
1. GET  /        -> shows an empty contact form (name, email, message).
2. POST /        -> receives the submitted form and validates it ON THE SERVER.
      - If anything is invalid: re-shows the form with visible error messages
        (and keeps whatever the user typed so they don't have to retype it).
      - If everything is valid: saves the message, then redirects to /thanks.
3. GET  /thanks  -> shows a confirmation page.

Why server-side validation?
---------------------------
Anything that runs in the browser (HTML "required", JavaScript) can be skipped
by anyone who sends a request directly (curl, a script, browser dev tools).
The server is the only place where validation can be trusted, so that is
where we do it. The small amount of JavaScript in the page is purely a
convenience (live character count, preventing double submits); the form works
fully with JavaScript turned off.

How to run
----------
    pip install flask
    python app.py
Then open http://127.0.0.1:5000
"""

import json
import os
import re
from datetime import datetime, timezone

from flask import Flask, redirect, render_template, request, session, url_for
from jinja2 import DictLoader

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

# Flask "sessions" are small bits of data stored in a signed cookie. We use one
# to pass the sender's name/email from the form handler to the thank-you page.
# The secret key is used to sign the cookie so it can't be tampered with.
# In production, set a fixed SECRET_KEY environment variable; the random
# fallback below changes on every restart (which just logs sessions out).
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

# ---------------------------------------------------------------------------
# Validation rules
# ---------------------------------------------------------------------------

# A practical email pattern. It checks for:
#   - a "local part" made of letters, digits, and common symbols
#   - exactly one "@"
#   - a domain with at least one dot (e.g. example.com), no spaces
# It's intentionally not the full RFC 5322 spec (which is huge and allows
# oddities nobody uses). The only 100% reliable check that an email address
# works is sending a message to it, but this catches typos and junk input.
EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"  # local part (before the @)
    r"@"
    r"[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$"   # domain, must contain a dot
)

# Upper limits protect us from absurdly large submissions. They are also sent
# to the template so the HTML `maxlength` attributes and the character counter
# always match what the server enforces.
LIMITS = {"name": 100, "email": 254, "message": 5000}

# The order fields appear on the page. Used to find the FIRST field with an
# error so we can move keyboard focus straight to it.
FIELD_ORDER = ("name", "email", "message")


def validate(name, email, message):
    """Check the three form fields and return a dict of error messages.

    The dict maps field name -> error text, e.g.
        {"name": "Enter your name."}
    An EMPTY dict means every field is valid.

    Error messages say what is wrong AND how to fix it, in plain language.

    The values passed in are expected to be already stripped of leading and
    trailing whitespace, so a field containing only spaces arrives here as ""
    and is treated as empty.
    """
    errors = {}

    # --- Name: required, not too long -------------------------------------
    if not name:
        errors["name"] = "Enter your name."
    elif len(name) > LIMITS["name"]:
        errors["name"] = f"Shorten your name to {LIMITS['name']} characters or fewer."

    # --- Email: required, correct format, not too long --------------------
    if not email:
        errors["email"] = "Enter your email address."
    elif len(email) > LIMITS["email"] or not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address, like name@example.com."

    # --- Message: required, not too long ----------------------------------
    if not message:
        errors["message"] = "Enter a message so we know how to help."
    elif len(message) > LIMITS["message"]:
        errors["message"] = f"Shorten your message to {LIMITS['message']:,} characters or fewer."

    return errors


# ---------------------------------------------------------------------------
# HTML templates
# ---------------------------------------------------------------------------
# To keep everything in one file, the templates live in a Python dict instead
# of a separate "templates/" folder. DictLoader tells Flask's template engine
# (Jinja) to look them up here. In a bigger project you'd move each one into
# templates/<name>.html and delete the DictLoader line below.
#
# Jinja basics used here:
#   {{ value }}            print a value (HTML-escaped automatically, which
#                          prevents users injecting HTML/JS into the page)
#   {% if ... %}...{% endif %}   conditional
#   {% macro name(args) %}       a reusable chunk of HTML (like a function)
#   {% extends "base.html" %}    reuse a parent layout
#   {% block body %}...{% endblock %}   the slot the child fills in

TEMPLATES = {
    # ---- Shared layout: page skeleton + design system ----------------------
    "base.html": """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {# Lets the browser style built-in controls (scrollbars etc.) for dark mode #}
  <meta name="color-scheme" content="light dark">
  <title>{{ title }}</title>
  <style>
    /* ------------------------------------------------------------------
       Design tokens: every colour lives here, so the whole page can switch
       between light and dark by redefining these few variables.
       ------------------------------------------------------------------ */
    :root {
      --page:          #eef1f6;   /* page background                      */
      --surface:       #ffffff;   /* the form panel                       */
      --field:         #f3f5f9;   /* resting background of inputs         */
      --ink:           #0f1a2b;   /* main text                            */
      --muted:         #566074;   /* hints, secondary text                */
      --line:          #d3d9e3;   /* borders                              */
      --accent:        #0b6e4f;   /* buttons, focus, success              */
      --accent-strong: #08543c;   /* button hover                         */
      --on-accent:     #ffffff;   /* text on top of the accent colour     */
      --ring:          rgba(11, 110, 79, .25);  /* focus halo             */
      --error:         #b42318;
      --error-bg:      #fdeceb;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --page:          #0d1119;
        --surface:       #151b26;
        --field:         #0d1119;
        --ink:           #e7ebf2;
        --muted:         #9aa5b8;
        --line:          #2c3544;
        --accent:        #3fd6a1;
        --accent-strong: #67e3b8;
        --on-accent:     #05241a;
        --ring:          rgba(63, 214, 161, .3);
        --error:         #ff8b80;
        --error-bg:      #2d1816;
      }
    }

    /* ------------------------------------------------------------------
       Base styles
       ------------------------------------------------------------------ */
    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      padding: clamp(1.5rem, 5vw, 4rem) 1.25rem;
      background: var(--page);
      color: var(--ink);
      /* System fonts: fast, no external requests, native look per device. */
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      font-size: 1rem;          /* 16px base; inputs must be >=16px or iOS zooms in */
      line-height: 1.5;
    }

    .page { max-width: 62rem; margin: 0 auto; }

    h1 {
      margin: 0 0 1rem;
      font-size: clamp(2.1rem, 5vw, 3.1rem);
      line-height: 1.08;
      letter-spacing: -0.025em;   /* large type reads better slightly tighter */
      font-weight: 700;
    }
    p { margin: 0 0 .75rem; }
    .muted { color: var(--muted); }

    /* Visible keyboard focus for links and buttons */
    a:focus-visible, button:focus-visible {
      outline: 3px solid var(--accent);
      outline-offset: 3px;
    }

    /* ------------------------------------------------------------------
       Form page layout: intro on the left, form on the right.
       On narrow screens the two stack, intro first.
       ------------------------------------------------------------------ */
    .split {
      display: grid;
      grid-template-columns: 1fr;
      gap: 2rem;
      align-items: start;
    }
    @media (min-width: 52rem) {
      .split { grid-template-columns: 5fr 7fr; gap: 4rem; }
      .intro { position: sticky; top: 2rem; }   /* stays put while a long message scrolls */
    }
    .intro p { max-width: 30ch; font-size: 1.125rem; }

    .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: clamp(1.25rem, 4vw, 2.25rem);
    }

    /* Summary banner shown above the form when validation fails */
    .summary {
      display: flex; gap: .6rem; align-items: center;
      margin-bottom: 1.5rem; padding: .75rem 1rem;
      background: var(--error-bg); color: var(--error);
      border-radius: 8px; font-weight: 600; font-size: .9375rem;
    }

    /* ------------------------------------------------------------------
       Fields
       ------------------------------------------------------------------ */
    .field { margin-bottom: 1.4rem; }

    label { display: block; margin-bottom: .2rem; font-weight: 600; font-size: .9375rem; }
    .hint { margin: 0 0 .5rem; color: var(--muted); font-size: .875rem; }

    input, textarea {
      display: block; width: 100%;
      padding: .75rem .9rem;
      min-height: 3rem;                 /* comfortable touch target */
      font: inherit;
      color: var(--ink);
      background: var(--field);
      border: 1.5px solid var(--line);
      border-radius: 8px;
      transition: border-color .15s, box-shadow .15s;
    }
    textarea { resize: vertical; min-height: 9rem; }

    input:hover, textarea:hover { border-color: var(--muted); }
    input:focus, textarea:focus {
      outline: none;                    /* replaced by border + halo below */
      border-color: var(--accent);
      box-shadow: 0 0 0 4px var(--ring);
    }

    /* Error state: red border and an icon + message. Colour is never the
       ONLY signal; the icon and text also say something is wrong. */
    .has-error input, .has-error textarea { border-color: var(--error); }
    .has-error input:focus, .has-error textarea:focus {
      box-shadow: 0 0 0 4px var(--error-bg);
    }

    /* Row under a field: error message on the left, character count right */
    .meta { display: flex; justify-content: space-between; gap: 1rem; margin-top: .45rem; }
    .error {
      display: flex; gap: .4rem; align-items: flex-start;
      margin: 0; color: var(--error); font-size: .875rem; font-weight: 600;
    }
    .error[hidden] { display: none; }   /* needed because .error sets display */
    .error svg { flex: none; margin-top: .15rem; }
    .counter { margin-left: auto; color: var(--muted); font-size: .8125rem;
               font-variant-numeric: tabular-nums; white-space: nowrap; }

    /* ------------------------------------------------------------------
       Buttons
       ------------------------------------------------------------------ */
    .btn {
      display: inline-flex; align-items: center; justify-content: center;
      min-height: 3rem; padding: 0 1.6rem;
      font: inherit; font-weight: 600;
      color: var(--on-accent); background: var(--accent);
      border: 0; border-radius: 8px;
      text-decoration: none; cursor: pointer;
      transition: background-color .15s;
    }
    .btn:hover { background: var(--accent-strong); }
    .btn:disabled { opacity: .7; cursor: progress; }
    .btn-block { width: 100%; }          /* full-width on phones, see below */
    @media (min-width: 40rem) { .btn-block { width: auto; } }

    /* ------------------------------------------------------------------
       Confirmation page
       ------------------------------------------------------------------ */
    .confirm { max-width: 32rem; margin: 0 auto; }
    .confirm p { font-size: 1.125rem; }
    .confirm .btn { margin-top: 1rem; }
    .check { display: block; margin-bottom: 1.5rem; }
    .check circle, .check path { stroke: var(--accent); }

    /* One deliberate moment of motion: the checkmark draws itself in
       response to the user's action. Skipped entirely for people who have
       asked their device to reduce motion. */
    @media (prefers-reduced-motion: no-preference) {
      .check circle { stroke-dasharray: 151; stroke-dashoffset: 151;
                      animation: draw .6s ease-out forwards; }
      .check path   { stroke-dasharray: 40;  stroke-dashoffset: 40;
                      animation: draw .35s .45s ease-out forwards; }
      @keyframes draw { to { stroke-dashoffset: 0; } }
    }
  </style>
</head>
<body>
  <main class="page">
    {% block body %}{% endblock %}
  </main>
  {% block scripts %}{% endblock %}
</body>
</html>
""",

    # ---- The contact form page ---------------------------------------------
    "form.html": """
{% extends "base.html" %}
{% block body %}

{# ---- Reusable pieces ------------------------------------------------- #}

{# Small "!" icon shown next to error messages. aria-hidden: the text already
   says everything a screen reader needs. #}
{% macro error_icon() %}
  <svg width="16" height="16" viewBox="0 0 20 20" aria-hidden="true" fill="none"
       stroke="currentColor" stroke-width="1.7" stroke-linecap="round">
    <circle cx="10" cy="10" r="8.5"/><path d="M10 5.8v5M10 13.7v.01"/>
  </svg>
{% endmacro %}

{# One form field: label, optional hint, the input itself, and an error row.
   Using a macro keeps the three fields consistent and the markup short.
     id            the field's name AND html id ("name", "email", "message")
     kind          "input" or "textarea"
     counter       show a live "x / max" character counter
   Macros can read `errors`, `values`, `limits` and `first_error` straight
   from the data the Flask view passes to the template. #}
{% macro field(id, label, kind="input", type="text", autocomplete="off",
               hint=none, counter=false) %}
  {% set err = errors.get(id) %}

  {# Tell assistive tech which hint / error text describes this field #}
  {% set described = [] %}
  {% if hint %}{% set _ = described.append(id ~ "-hint") %}{% endif %}
  {% if err %}{% set _ = described.append(id ~ "-error") %}{% endif %}

  <div class="field{{ ' has-error' if err }}">
    <label for="{{ id }}">{{ label }}</label>
    {% if hint %}<p class="hint" id="{{ id }}-hint">{{ hint }}</p>{% endif %}

    {% if kind == "textarea" %}
      <textarea id="{{ id }}" name="{{ id }}" rows="6" maxlength="{{ limits[id] }}"
        {% if err %}aria-invalid="true"{% endif %}
        {% if described %}aria-describedby="{{ described|join(' ') }}"{% endif %}
        {% if first_error == id %}autofocus{% endif %}>{{ values[id] }}</textarea>
    {% else %}
      <input id="{{ id }}" name="{{ id }}" type="{{ type }}" value="{{ values[id] }}"
        maxlength="{{ limits[id] }}" autocomplete="{{ autocomplete }}"
        {% if type == "email" %}autocapitalize="none" spellcheck="false"{% endif %}
        {% if err %}aria-invalid="true"{% endif %}
        {% if described %}aria-describedby="{{ described|join(' ') }}"{% endif %}
        {% if first_error == id %}autofocus{% endif %}>
    {% endif %}

    {% if err or counter %}
      <div class="meta">
        {% if err %}
          <p class="error" id="{{ id }}-error">{{ error_icon() }}<span>{{ err }}</span></p>
        {% endif %}
        {% if counter %}
          {# Server renders the starting count; JavaScript keeps it updated #}
          <span class="counter" data-counter>{{ values[id]|length }} / {{ limits[id] }}</span>
        {% endif %}
      </div>
    {% endif %}
  </div>
{% endmacro %}

{# ---- The page itself ------------------------------------------------- #}
<div class="split">

  <div class="intro">
    <h1>Send us a message</h1>
    <p>Tell us what you need and we'll reply by email.</p>
    <p class="muted">All fields are required.</p>
  </div>

  <div class="panel">
    {# role="alert" makes screen readers announce this as soon as it appears #}
    {% if errors %}
      <div class="summary" role="alert">
        {{ error_icon() }}
        {% set n = errors|length %}
        <span>{{ n }} {{ 'field needs' if n == 1 else 'fields need' }} fixing before we can send your message.</span>
      </div>
    {% endif %}

    {# "novalidate" turns off the browser's built-in validation pop-ups so that
       our SERVER-side validation is what the user always sees. #}
    <form method="post" action="{{ url_for('contact') }}" novalidate data-contact>
      {{ field("name", "Name", autocomplete="name") }}
      {{ field("email", "Email", type="email", autocomplete="email",
               hint="We'll reply to this address.") }}
      {{ field("message", "Message", kind="textarea", counter=true,
               hint="Include any details that will help us reply.") }}

      <button class="btn btn-block" type="submit" data-label="Send message">Send message</button>
    </form>
  </div>

</div>
{% endblock %}

{# Optional enhancements. Everything above works without this script. #}
{% block scripts %}
<script>
(function () {
  var form = document.querySelector("form[data-contact]");
  if (!form) return;
  var button = form.querySelector("button[type=submit]");

  form.querySelectorAll("input, textarea").forEach(function (el) {
    el.addEventListener("input", function () {
      var wrap = el.closest(".field");

      // 1. Once the user starts fixing a field, clear its error right away
      //    (the server re-checks everything on submit anyway).
      if (wrap.classList.contains("has-error")) {
        wrap.classList.remove("has-error");
        el.removeAttribute("aria-invalid");
        var err = wrap.querySelector(".error");
        if (err) err.hidden = true;
      }

      // 2. Keep the live character counter up to date.
      var counter = wrap.querySelector("[data-counter]");
      if (counter) counter.textContent = el.value.length + " / " + el.maxLength;
    });
  });

  // 3. Prevent double submits: disable the button and show progress.
  form.addEventListener("submit", function () {
    button.disabled = true;
    button.textContent = "Sending\\u2026";
  });

  // 4. If the user comes back with the browser's Back button, the page may be
  //    restored from cache with the button still disabled. Reset it.
  window.addEventListener("pageshow", function (e) {
    if (e.persisted) {
      button.disabled = false;
      button.textContent = button.dataset.label;
    }
  });
})();
</script>
{% endblock %}
""",

    # ---- The confirmation page ---------------------------------------------
    "thanks.html": """
{% extends "base.html" %}
{% block body %}
<section class="confirm">
  {# Decorative animated checkmark (the animation is defined in base.html) #}
  <svg class="check" width="56" height="56" viewBox="0 0 52 52" aria-hidden="true"
       fill="none" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="26" cy="26" r="24" stroke-width="3"/>
    <path d="M15 27l8 8 14-16"/>
  </svg>

  {# The button on the form says "Send message"; this page confirms the same
     action in the past tense. #}
  <h1>Message sent</h1>
  <p>Thanks, {{ name }}. We'll reply to <strong>{{ email }}</strong>.</p>
  <a class="btn" href="{{ url_for('contact') }}">Send another message</a>
</section>
{% endblock %}
""",
}

# Tell Flask to load templates from the dict above instead of from disk.
app.jinja_loader = DictLoader(TEMPLATES)


# ---------------------------------------------------------------------------
# Routes (the URLs the app responds to)
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def contact():
    """Show the form (GET) and process a submission (POST)."""

    # Start with blank values and no errors. This is what a first visit
    # (a plain GET request) displays.
    values = {"name": "", "email": "", "message": ""}
    errors = {}

    if request.method == "POST":
        # Read each field from the submitted form. .get(key, "") returns ""
        # if the field is missing entirely (e.g. someone crafted a request
        # without it), and .strip() removes leading/trailing whitespace so a
        # field containing only spaces counts as empty.
        values = {key: request.form.get(key, "").strip() for key in values}

        # Browsers send line breaks in a <textarea> as "\r\n" (two characters),
        # but the browser's maxlength counts them as one. Normalising to "\n"
        # keeps the server's length check consistent with what the user sees
        # in the character counter.
        values["message"] = values["message"].replace("\r\n", "\n")

        # Run the validation rules; `errors` is empty if all is well.
        errors = validate(**values)

        if not errors:
            # --- Success path ---------------------------------------------
            # Save the message. Here we append one JSON object per line to a
            # file. In a real app you would send an email or insert into a
            # database instead.
            record = {**values, "received_at": datetime.now(timezone.utc).isoformat()}
            with open("messages.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            # Remember who submitted so the thank-you page can greet them.
            # (Only name and email: cookies are limited to ~4 KB, so the
            # message itself must not go in here.)
            session["submitted"] = {"name": values["name"], "email": values["email"]}

            # Redirect instead of rendering the thank-you page directly.
            # This is the "Post/Redirect/Get" pattern: if the user refreshes
            # the confirmation page, the browser repeats a harmless GET rather
            # than re-submitting the form (which would send a duplicate).
            return redirect(url_for("thanks"))

    # --- Failure path (or first visit) --------------------------------------
    # Re-render the form. On a failed POST this shows the error messages and
    # the user's previous input. HTTP 400 ("Bad Request") signals that the
    # submission was invalid; a normal first visit returns 200.
    status = 400 if errors else 200

    # The first invalid field (in page order) receives keyboard focus, so the
    # user lands right where they need to fix something.
    first_error = next((f for f in FIELD_ORDER if f in errors), None)

    # Putting "Error:" at the start of the tab title helps screen-reader users
    # notice that the page reloaded with a problem.
    title = "Error: Send us a message" if errors else "Send us a message"

    return render_template("form.html", title=title, values=values,
                           errors=errors, limits=LIMITS,
                           first_error=first_error), status


@app.route("/thanks")
def thanks():
    """Confirmation page shown after a successful submission."""

    # pop() reads the value AND removes it from the session, so the page can
    # only be seen once per submission.
    data = session.pop("submitted", None)

    # If someone opens /thanks directly (without having just submitted the
    # form), there's nothing to confirm, so send them to the form instead.
    if not data:
        return redirect(url_for("contact"))

    return render_template("thanks.html", title="Message sent", **data)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Runs Flask's built-in development server. debug=True gives helpful error
    # pages and auto-reloads on code changes. NEVER use debug=True in
    # production; deploy behind a real server such as gunicorn instead.
    app.run(debug=True)
