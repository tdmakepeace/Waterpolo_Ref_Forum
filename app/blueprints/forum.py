from datetime import datetime, timezone

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import desc

from app.extensions import db
from app.forms import QuestionForm, ReplyForm
from app.models.question import (
    STATUS_CLOSED,
    STATUS_LOCKED,
    STATUS_OPEN,
    Question,
)
from app.models.reply import Reply
from app.models.vote import Vote, refresh_question_score
from app.permissions import supervisor_required

forum_bp = Blueprint("forum", __name__)


def public_question_query():
    return Question.query.filter_by(is_hidden=False)


def visible_question_or_404(question_id):
    question = Question.query.get_or_404(question_id)
    user = current_user if current_user.is_authenticated else None
    if not question.visible_to(user):
        abort(404)
    return question


def listing_query(tab, include_hidden=False):
    query = Question.query
    if tab == "hidden":
        query = query.filter_by(is_hidden=True)
        if current_user.is_authenticated and not current_user.is_staff:
            query = query.filter_by(user_id=current_user.id)
    elif tab == "closed":
        query = query.filter(
            Question.is_hidden.is_(False),
            Question.status.in_((STATUS_CLOSED, STATUS_LOCKED)),
        )
    else:
        query = query.filter(Question.is_hidden.is_(False), Question.status == STATUS_OPEN)
    return query.order_by(desc(Question.score), desc(Question.created_at))


@forum_bp.route("/questions")
def list_questions():
    tab = request.args.get("tab", "open")
    if tab not in ("open", "closed", "hidden"):
        tab = "open"
    if tab == "hidden" and not current_user.is_authenticated:
        abort(404)
    questions = listing_query(tab).all()
    return render_template(
        "forum/list.html", questions=questions, tab=tab, votes_by_question=_vote_map(questions)
    )


def _vote_map(questions):
    if not current_user.is_authenticated or not questions:
        return {}
    ids = [q.id for q in questions]
    votes = Vote.query.filter(
        Vote.user_id == current_user.id, Vote.question_id.in_(ids)
    ).all()
    return {v.question_id: v.value for v in votes}


@forum_bp.route("/questions/new", methods=["GET", "POST"])
@login_required
def new_question():
    form = QuestionForm()
    if form.validate_on_submit():
        question = Question(
            user_id=current_user.id,
            author_nickname=current_user.nickname,
            title=form.title.data.strip(),
            body=form.body.data.strip(),
            status=STATUS_OPEN,
        )
        db.session.add(question)
        db.session.commit()
        flash("Question posted.", "success")
        return redirect(url_for("forum.detail", question_id=question.id))
    return render_template("forum/new.html", form=form)


@forum_bp.route("/questions/<int:question_id>", methods=["GET", "POST"])
def detail(question_id):
    question = visible_question_or_404(question_id)
    form = ReplyForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))
        if not question.is_open_for_replies:
            flash("This thread is closed to new replies.", "warning")
            return redirect(url_for("forum.detail", question_id=question.id))
        reply = Reply(
            question_id=question.id,
            user_id=current_user.id,
            author_nickname=current_user.nickname,
            body=form.body.data.strip(),
        )
        question.updated_at = datetime.now(timezone.utc)
        db.session.add(reply)
        db.session.commit()
        flash("Reply posted.", "success")
        return redirect(url_for("forum.detail", question_id=question.id))
    user_vote = None
    if current_user.is_authenticated:
        vote = Vote.query.filter_by(
            user_id=current_user.id, question_id=question.id
        ).first()
        user_vote = vote.value if vote else None
    return render_template(
        "forum/detail.html", question=question, form=form, user_vote=user_vote
    )


@forum_bp.route("/questions/<int:question_id>/vote/<direction>", methods=["POST"])
@login_required
def vote(question_id, direction):
    question = visible_question_or_404(question_id)
    if direction not in ("up", "down"):
        abort(400)
    value = 1 if direction == "up" else -1
    existing = Vote.query.filter_by(
        user_id=current_user.id, question_id=question.id
    ).first()
    if existing and existing.value == value:
        db.session.delete(existing)
    elif existing:
        existing.value = value
    else:
        db.session.add(
            Vote(user_id=current_user.id, question_id=question.id, value=value)
        )
    db.session.flush()
    refresh_question_score(question)
    db.session.commit()
    return redirect(request.referrer or url_for("forum.detail", question_id=question.id))


@forum_bp.route("/questions/<int:question_id>/close", methods=["POST"])
@login_required
def close(question_id):
    question = visible_question_or_404(question_id)
    if question.user_id != current_user.id and not current_user.is_staff:
        abort(403)
    if question.status == STATUS_LOCKED and not current_user.is_staff:
        flash("This thread is locked by staff.", "warning")
        return redirect(url_for("forum.detail", question_id=question.id))
    question.status = STATUS_CLOSED
    db.session.commit()
    flash("Question closed.", "info")
    return redirect(url_for("forum.detail", question_id=question.id))


@forum_bp.route("/questions/<int:question_id>/reopen", methods=["POST"])
@login_required
def reopen(question_id):
    question = visible_question_or_404(question_id)
    if question.user_id != current_user.id and not current_user.is_staff:
        abort(403)
    if question.status == STATUS_LOCKED and not current_user.is_staff:
        flash("This thread is locked by staff and cannot be reopened.", "warning")
        return redirect(url_for("forum.detail", question_id=question.id))
    question.status = STATUS_OPEN
    db.session.commit()
    flash("Question reopened.", "success")
    return redirect(url_for("forum.detail", question_id=question.id))


@forum_bp.route("/questions/<int:question_id>/lock", methods=["POST"])
@supervisor_required
def lock(question_id):
    question = Question.query.get_or_404(question_id)
    question.status = STATUS_LOCKED
    db.session.commit()
    flash("Thread locked.", "info")
    return redirect(url_for("forum.detail", question_id=question.id))


@forum_bp.route("/questions/<int:question_id>/unlock", methods=["POST"])
@supervisor_required
def unlock(question_id):
    question = Question.query.get_or_404(question_id)
    question.status = STATUS_OPEN
    db.session.commit()
    flash("Thread unlocked.", "success")
    return redirect(url_for("forum.detail", question_id=question.id))


@forum_bp.route("/questions/<int:question_id>/hide", methods=["POST"])
@supervisor_required
def hide(question_id):
    question = Question.query.get_or_404(question_id)
    question.is_hidden = True
    db.session.commit()
    flash("Thread hidden.", "info")
    return redirect(url_for("forum.detail", question_id=question.id))


@forum_bp.route("/questions/<int:question_id>/unhide", methods=["POST"])
@supervisor_required
def unhide(question_id):
    question = Question.query.get_or_404(question_id)
    question.is_hidden = False
    db.session.commit()
    flash("Thread is visible again.", "success")
    return redirect(url_for("forum.detail", question_id=question.id))


@forum_bp.route("/questions/<int:question_id>/delete", methods=["POST"])
@supervisor_required
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    flash("Question deleted.", "info")
    return redirect(url_for("forum.list_questions"))


@forum_bp.route("/replies/<int:reply_id>/delete", methods=["POST"])
@supervisor_required
def delete_reply(reply_id):
    reply = Reply.query.get_or_404(reply_id)
    question_id = reply.question_id
    db.session.delete(reply)
    db.session.commit()
    flash("Reply deleted.", "info")
    return redirect(url_for("forum.detail", question_id=question_id))
