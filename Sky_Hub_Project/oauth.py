"""
oauth.py — Google OAuth 2.0 integration using Authlib
Handles: login, callback, token exchange, user creation/lookup
"""
import os
import uuid
import urllib.request

from authlib.integrations.flask_client import OAuth
from flask import (
    Blueprint, redirect, url_for, session, flash, current_app
)
from flask_login import login_user, current_user

# ─────────────────────────────────────────────────────────────────────────────
#  Blueprint
# ─────────────────────────────────────────────────────────────────────────────

google_bp = Blueprint("google_auth", __name__, url_prefix="/auth")

# Module-level OAuth object (registered on app in create_app / app.py)
oauth = OAuth()

google = oauth.register(
    name="google",
    # Credentials come from environment variables (set in .env / your OS)
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    # Discovery URL — automatically fetches endpoints, scopes, JWKS, etc.
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",   # minimum required scopes
    },
)


# ─────────────────────────────────────────────────────────────────────────────
#  Routes
# ─────────────────────────────────────────────────────────────────────────────

@google_bp.route("/google/login")
def google_login():
    """Redirect the user to Google's OAuth consent screen."""
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    # Generate a cryptographic nonce (prevents replay attacks)
    nonce = uuid.uuid4().hex
    session["oauth_nonce"] = nonce

    redirect_uri = url_for("google_auth.google_callback", _external=True)
    return google.authorize_redirect(redirect_uri, nonce=nonce)


@google_bp.route("/google/callback")
def google_callback():
    """Google redirects here after the user approves (or denies) access."""
    # Lazy import to avoid circular imports
    from models import db, User

    # ── 1. Exchange auth code for tokens ──────────────────────────────────
    try:
        token = google.authorize_access_token()
    except Exception as exc:
        current_app.logger.error("OAuth token exchange failed: %s", exc)
        flash("Google sign-in failed. Please try again.", "danger")
        return redirect(url_for("login"))

    # ── 2. Validate ID token (nonce check prevents replay) ────────────────
    nonce = session.pop("oauth_nonce", None)
    try:
        user_info = google.parse_id_token(token, nonce=nonce)
    except Exception as exc:
        current_app.logger.error("ID token validation failed: %s", exc)
        flash("Authentication error. Please try again.", "danger")
        return redirect(url_for("login"))

    google_id = user_info.get("sub")          # unique Google user ID
    email     = user_info.get("email", "")
    name      = user_info.get("name", "")
    picture   = user_info.get("picture", "")  # Google-hosted avatar URL

    if not google_id or not email:
        flash("Could not retrieve your Google account details.", "danger")
        return redirect(url_for("login"))

    # ── 3. Find or create the user ────────────────────────────────────────
    user = User.query.filter_by(google_id=google_id).first()

    if user is None:
        # Maybe the email already exists (local account) — link Google ID
        user = User.query.filter_by(email=email).first()
        if user:
            user.google_id = google_id
            db.session.commit()
        else:
            # Brand new user — download Google profile picture
            profile_fn = _download_google_picture(picture, current_app)

            # Sanitise username: replace spaces, ensure uniqueness
            base_username = name.replace(" ", "_").lower()[:40]
            username = _unique_username(base_username)

            user = User(
                username=user_info.get("given_name", username)[:50] or username,
                email=email,
                google_id=google_id,
                profile_image=profile_fn,
                available_for_project=True,
            )
            db.session.add(user)
            db.session.commit()
            flash(f"Welcome to CS Community, {user.username}! "
                  "Complete your profile to get started.", "success")

    # ── 4. Log the user in ────────────────────────────────────────────────
    login_user(user, remember=False)
    return redirect(url_for("home"))


# ─────────────────────────────────────────────────────────────────────────────
#  Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _download_google_picture(picture_url: str, app) -> str:
    """
    Download a Google profile picture to static/uploads/profile_pics/.
    Returns the filename (not full path).
    Falls back to default_profile.png on any error.
    """
    if not picture_url:
        return "default_profile.png"
    try:
        ext = ".jpg"
        filename = uuid.uuid4().hex + ext
        dest = os.path.join(
            app.root_path, "static", "uploads", "profile_pics", filename
        )
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        urllib.request.urlretrieve(picture_url, dest)   # nosec (trusted Google URL)
        return filename
    except Exception as exc:
        app.logger.warning("Could not download Google avatar: %s", exc)
        return "default_profile.png"


def _unique_username(base: str) -> str:
    """Append a short UUID suffix if the username is already taken."""
    from models import User
    candidate = base or "user"
    if not User.query.filter_by(username=candidate).first():
        return candidate
    suffix = uuid.uuid4().hex[:6]
    return f"{candidate}_{suffix}"
