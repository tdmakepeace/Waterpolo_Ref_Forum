from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, UniqueConstraint, func

from app.extensions import db


class Vote(db.Model):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_vote_user_question"),
        CheckConstraint("value IN (-1, 1)", name="ck_vote_value"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    value = db.Column(db.SmallInteger, nullable=False)
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

    user = db.relationship("User", back_populates="votes")
    question = db.relationship("Question", back_populates="votes")


def refresh_question_score(question):
    total = (
        db.session.query(func.coalesce(func.sum(Vote.value), 0))
        .filter(Vote.question_id == question.id)
        .scalar()
    )
    question.score = int(total or 0)
    return question.score
