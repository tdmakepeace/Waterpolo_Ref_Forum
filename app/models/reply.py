from datetime import datetime, timezone

from app.extensions import db


class Reply(db.Model):
    __tablename__ = "replies"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author_nickname = db.Column(db.String(80), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_high_quality = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    question = db.relationship("Question", back_populates="replies")
    author = db.relationship("User", back_populates="replies")
