import os
import uuid
from flask import (
    Flask, render_template, url_for, redirect,
    request, flash, abort, session
)
from flask_login import (
    LoginManager, login_user, logout_user, current_user, login_required
)
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from forms import (
    RegistrationForm, LoginForm, PostForm, CommentForm,
    LikeForm, DeleteForm, EditProfileForm
)
from models import db, User, Post, Comment, Like
from config import DevConfig

# ─────────────────────────────────────────────────────────────────────────────
#  App Factory / Configuration
# ─────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config.from_object(DevConfig)

# Upload root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
CV_FOLDER = os.path.join(UPLOAD_FOLDER, "cv")
PICTURE_FOLDER = os.path.join(UPLOAD_FOLDER, "profile_pics")

for folder in [UPLOAD_FOLDER, CV_FOLDER, PICTURE_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB hard limit

db.init_app(app)


login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access CS Community."
login_manager.login_message_category = "info"

# ─────────────────────────────────────────────────────────────────────────────
#  Helper Utilities
# ─────────────────────────────────────────────────────────────────────────────

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}
ALLOWED_CV_EXTENSIONS = {"pdf"}


def _allowed_file(filename: str, allowed: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def save_picture(form_picture) -> str:
    """
    Resize, save, and return ONLY the filename (not a full path).
    Stored at: static/uploads/profile_pics/<uuid>.<ext>
    """
    random_hex = uuid.uuid4().hex
    _, f_ext = os.path.splitext(secure_filename(form_picture.filename))
    f_ext = f_ext.lower()
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(PICTURE_FOLDER, picture_fn)

    try:
        from PIL import Image
        output_size = (300, 300)
        img = Image.open(form_picture)
        img.thumbnail(output_size)
        img.save(picture_path)
    except Exception:
        # PIL unavailable — save raw file
        form_picture.seek(0)
        form_picture.save(picture_path)

    return picture_fn   # ← ONLY filename, never a full path


def save_cv(form_cv) -> str:
    """
    Save uploaded PDF resume.
    Returns ONLY the filename (not a full path).
    """
    random_hex = uuid.uuid4().hex
    _, f_ext = os.path.splitext(secure_filename(form_cv.filename))
    cv_fn = random_hex + f_ext.lower()
    cv_path = os.path.join(CV_FOLDER, cv_fn)
    form_cv.save(cv_path)
    return cv_fn   # ← ONLY filename


def profile_image_url(filename: str) -> str:
    """
    Always returns a valid URL for a profile image.
    Falls back to default_profile.png if filename is missing or empty.
    """
    fn = filename if filename else "default_profile.png"
    return url_for("static", filename=f"uploads/profile_pics/{fn}")


# Expose helper to Jinja2 templates
app.jinja_env.globals["profile_image_url"] = profile_image_url

# ─────────────────────────────────────────────────────────────────────────────
#  User Loader
# ─────────────────────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ─────────────────────────────────────────────────────────────────────────────
#  Public Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def landing():
    """CS Community welcome/marketing page."""
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    form = RegistrationForm()
    if form.validate_on_submit():
        if User.query.filter(
            (User.username == form.username.data) | (User.email == form.email.data)
        ).first():
            flash("Username or email already registered.", "warning")
        else:
            # Handle optional file uploads
            cv_filename = None
            if form.cv_file.data and form.cv_file.data.filename:
                cv_filename = save_cv(form.cv_file.data)

            profile_fn = "default_profile.png"
            if form.profile_image.data and form.profile_image.data.filename:
                profile_fn = save_picture(form.profile_image.data)

            user = User(
                username=form.username.data,
                email=form.email.data,
                track=form.track.data,
                skills=form.skills.data,
                available_for_project=form.available_for_project.data,
                cv_file=cv_filename,
                profile_image=profile_fn,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash("Welcome to CS Community! Your account is ready.", "success")
            return redirect(url_for("login"))

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=False)
            next_page = request.args.get("next")
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(next_page or url_for("home"))
        flash("Incorrect email or password.", "danger")

    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have signed out of CS Community.", "info")
    return redirect(url_for("login"))

# ─────────────────────────────────────────────────────────────────────────────
#  Protected Routes — Feed & Filtering
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/home")
@login_required
def home():
    """
    Main feed with optional GET-based filters:
      ?track=Web Development
      ?available=yes
    Both can be combined.
    """
    track_filter = request.args.get("track", "").strip()
    available_filter = request.args.get("available", "").strip()

    query = Post.query.join(User)

    if track_filter:
        query = query.filter(User.track == track_filter)

    if available_filter == "yes":
        query = query.filter(User.available_for_project == True)

    posts = query.order_by(Post.date.desc()).all()

    return render_template(
        "home.html",
        posts=posts,
        track_filter=track_filter,
        available_filter=available_filter,
    )

# ─────────────────────────────────────────────────────────────────────────────
#  Profile Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/profile/<int:user_id>")
@login_required
def profile(user_id):
    user = User.query.get_or_404(user_id)
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.date.desc()).all()
    total_likes = sum((p.likes_count or 0) for p in posts)
    return render_template("profile.html", user=user, posts=posts, total_likes=total_likes)


@app.route("/me")
@login_required
def me():
    return redirect(url_for("profile", user_id=current_user.id))


@app.route("/network")
@login_required
def network():
    """
    People-first discovery page.
    Filters operate via GET params: ?search=&track=&available=yes
    Users are ordered: available first, then alphabetical username.
    """
    search_q      = request.args.get("search", "").strip()
    track_filter  = request.args.get("track", "").strip()
    avail_filter  = request.args.get("available", "").strip()

    # Start with everyone except the current user
    query = User.query.filter(User.id != current_user.id)

    # Full-text search across username, skills, and track (case-insensitive)
    if search_q:
        like = f"%{search_q}%"
        query = query.filter(
            db.or_(
                User.username.ilike(like),
                User.skills.ilike(like),
                User.track.ilike(like),
            )
        )

    if track_filter:
        query = query.filter(User.track == track_filter)

    if avail_filter == "yes":
        query = query.filter(User.available_for_project == True)

    # Available first, then A→Z
    users = query.order_by(
        User.available_for_project.desc(),
        User.username.asc()
    ).all()

    return render_template(
        "network.html",
        users=users,
        search_q=search_q,
        track_filter=track_filter,
        avail_filter=avail_filter,
        total=len(users),
    )


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.track = form.track.data
        current_user.skills = form.skills.data
        current_user.available_for_project = form.available_for_project.data
        current_user.github_link = form.github_link.data or None
        current_user.portfolio_link = form.portfolio_link.data or None
        current_user.linkedin_link = form.linkedin_link.data or None
        current_user.phone_number = form.phone_number.data or None

        if form.cv_file.data and form.cv_file.data.filename:
            current_user.cv_file = save_cv(form.cv_file.data)

        if form.profile_image.data and form.profile_image.data.filename:
            current_user.profile_image = save_picture(form.profile_image.data)

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile", user_id=current_user.id))

    elif request.method == "GET":
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.track.data = current_user.track
        form.skills.data = current_user.skills
        form.available_for_project.data = current_user.available_for_project
        form.github_link.data = current_user.github_link
        form.portfolio_link.data = current_user.portfolio_link
        form.linkedin_link.data = current_user.linkedin_link
        form.phone_number.data = current_user.phone_number

    return render_template("edit_profile.html", form=form)

# ─────────────────────────────────────────────────────────────────────────────
#  Post Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/new", methods=["GET", "POST"])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        image_filename = None
        video_filename = None

        if form.image.data and form.image.data.filename:
            image_file = form.image.data
            image_filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))

        if form.video.data and form.video.data.filename:
            video_file = form.video.data
            video_filename = secure_filename(video_file.filename)
            video_file.save(os.path.join(app.config["UPLOAD_FOLDER"], video_filename))

        # Auto-generate title from first 80 chars of content if not provided
        content_text = form.content.data or ""
        auto_title = (form.title.data or "").strip()
        if not auto_title:
            auto_title = content_text[:80].strip()
            if len(content_text) > 80:
                auto_title += "…"

        post = Post(
            title=auto_title or "Untitled",
            content=content_text,
            image_file=image_filename,
            video_file=video_filename,
            author=current_user,
        )
        db.session.add(post)
        db.session.commit()
        flash("Post published to CS Community.", "success")
        return redirect(url_for("post_detail", post_id=post.id))

    return render_template("new_post.html", form=form)



@app.route("/post/<int:post_id>")
@login_required
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.date.asc()).all()
    liked = Like.query.filter_by(user_id=current_user.id, post_id=post.id).first() is not None

    return render_template(
        "post_detail.html",
        post=post,
        comments=comments,
        form=CommentForm(),
        like_form=LikeForm(),
        delete_form=DeleteForm(),
        comment_delete_form=DeleteForm(),
        liked=liked,
    )


@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        abort(403)
    form = PostForm(obj=post)
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        if form.image.data and form.image.data.filename:
            image_filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))
            post.image_file = image_filename
        if form.video.data and form.video.data.filename:
            video_filename = secure_filename(form.video.data.filename)
            form.video.data.save(os.path.join(app.config["UPLOAD_FOLDER"], video_filename))
            post.video_file = video_filename
        db.session.commit()
        flash("Post updated.", "success")
        return redirect(url_for("post_detail", post_id=post.id))
    return render_template("edit_post.html", form=form, post=post)


@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash("Post deleted.", "info")
    return redirect(url_for("home"))

# ─────────────────────────────────────────────────────────────────────────────
#  Comment Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, author=current_user, post=post)
        db.session.add(comment)
        db.session.commit()
        flash("Comment posted.", "success")
    else:
        flash("Comment could not be posted.", "warning")
    return redirect(url_for("post_detail", post_id=post.id))


@app.route("/comment/<int:comment_id>/edit", methods=["GET", "POST"])
@login_required
def edit_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.user_id != current_user.id:
        abort(403)
    form = CommentForm(obj=comment)
    if form.validate_on_submit():
        comment.content = form.content.data
        db.session.commit()
        flash("Comment updated.", "success")
        return redirect(url_for("post_detail", post_id=comment.post_id))
    return render_template("edit_comment.html", form=form, comment=comment)


@app.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.user_id != current_user.id:
        abort(403)
    post_id = comment.post_id
    db.session.delete(comment)
    db.session.commit()
    flash("Comment deleted.", "info")
    return redirect(url_for("post_detail", post_id=post_id))

# ─────────────────────────────────────────────────────────────────────────────
#  Like Route
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/post/<int:post_id>/like", methods=["POST"])
@login_required
def toggle_like(post_id):
    post = Post.query.get_or_404(post_id)
    existing = Like.query.filter_by(user_id=current_user.id, post_id=post.id).first()
    if existing:
        db.session.delete(existing)
        post.likes_count = max((post.likes_count or 1) - 1, 0)
        flash("Like removed.", "info")
    else:
        db.session.add(Like(user_id=current_user.id, post_id=post.id))
        post.likes_count = (post.likes_count or 0) + 1
        flash("Post liked!", "success")
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Database error. Please try again.", "danger")
    return redirect(url_for("post_detail", post_id=post.id))

# ─────────────────────────────────────────────────────────────────────────────
#  Utility Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/clear_session")
def clear_session():
    """Emergency session clear (dev use)."""
    session.clear()
    logout_user()
    flash("Session cleared.", "info")
    return redirect(url_for("login"))


# ─────────────────────────────────────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
