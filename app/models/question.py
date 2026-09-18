from datetime import datetime, timezone

from app.extensions import db

STATUS_OPEN = "open"
STATUS_CLOSED = "closed_by_owner"
STATUS_LOCKED = "locked_by_admin"


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author_nickname = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default=STATUS_OPEN)
    is_hidden = db.Column(db.Boolean, nullable=False, default=False)
    score = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    author = db.relationship("User", back_populates="questions")
    replies = db.relationship(
        "Reply",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="Reply.created_at",
    )
    votes = db.relationship(
        "Vote", back_populates="question", cascade="all, delete-orphan"
    )

    @property
    def is_open_for_replies(self):
        return self.status == STATUS_OPEN

    @property
    def is_closed_tab(self):
        return self.status in (STATUS_CLOSED, STATUS_LOCKED)

    def visible_to(self, user):
        if not self.is_hidden:
            return True
        if user is None or not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "is_staff", False):
            return True
        return user.id == self.user_id
