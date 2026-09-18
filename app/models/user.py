from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(80), unique=True, nullable=False)
    real_name = db.Column(db.String(120), nullable=True)
    role = db.Column(db.String(20), nullable=False, default="user")
    status = db.Column(db.String(30), nullable=False, default="pending_approval")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_bootstrap_admin = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    questions = db.relationship("Question", back_populates="author", lazy="dynamic")
    replies = db.relationship("Reply", back_populates="author", lazy="dynamic")
    votes = db.relationship("Vote", back_populates="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_staff(self):
        return self.role in ("supervisor", "admin")

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def can_login(self):
        return bool(self.is_active) and self.status == "approved"

    def get_id(self):
        return str(self.id)
