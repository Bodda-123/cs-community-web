from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model, UserMixin):
    """Platform member — CS Community academic network."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    # Academic identity fields
    track = db.Column(db.String(50), nullable=True)           # e.g. "Web Development", "AI & ML"
    skills = db.Column(db.String(200), nullable=True)          # comma-separated, e.g. "Python, React"
    available_for_project = db.Column(db.Boolean, default=True, nullable=False)

    # Contact & portfolio links
    github_link = db.Column(db.String(200), nullable=True)
    portfolio_link = db.Column(db.String(200), nullable=True)
    linkedin_link = db.Column(db.String(200), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)     # WhatsApp contact

    # File uploads — stored as filename only (not full path)
    cv_file = db.Column(db.String(150), nullable=True)
    profile_image = db.Column(db.String(150), nullable=False, default='default_profile.png')

    # Relationships
    posts = db.relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = db.relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    likes = db.relationship("Like", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        """Hash and store the password securely."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def has_liked(self, post) -> bool:
        """Return True if this user has already liked the given post."""
        return any(like.post_id == post.id for like in self.likes)

    def get_profile_image_url(self):
        """Return the correct filename for the profile image, falling back to default."""
        return self.profile_image if self.profile_image else 'default_profile.png'


class Post(db.Model):
    """A member's post/update on the CS Community feed."""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    image_file = db.Column(db.String(150), nullable=True)
    video_file = db.Column(db.String(150), nullable=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    author = db.relationship("User", back_populates="posts")
    likes_count = db.Column(db.Integer, nullable=False, default=0)

    comments = db.relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    likes = db.relationship("Like", back_populates="post", cascade="all, delete-orphan")


class Comment(db.Model):
    """A comment left on a post."""

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    post_id = db.Column(
        db.Integer, db.ForeignKey("post.id", ondelete="CASCADE"), nullable=False
    )

    author = db.relationship("User", back_populates="comments")
    post = db.relationship("Post", back_populates="comments")


class Like(db.Model):
    """A like reaction on a post (unique per user per post)."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    post_id = db.Column(
        db.Integer, db.ForeignKey("post.id", ondelete="CASCADE"), nullable=False
    )
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="likes")
    post = db.relationship("Post", back_populates="likes")

    __table_args__ = (db.UniqueConstraint("user_id", "post_id", name="uix_user_post"),)
