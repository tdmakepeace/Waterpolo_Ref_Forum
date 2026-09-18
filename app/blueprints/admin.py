from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import desc

from app.extensions import db
from app.forms import ResourceLinkForm, UserForm
from app.models.password_reset import PasswordResetToken
from app.models.question import Question
from app.models.resource_link import ResourceLink
from app.models.user import User
from app.nicknames import resolve_nickname
from app.permissions import admin_required, supervisor_required
from app.tokens import issue_reset_token

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@supervisor_required
def dashboard():
    pending_count = User.query.filter_by(status="pending_approval").count()
    reset_count = PasswordResetToken.query.filter_by(used_at=None, token_hash=None).count()
    question_count = Question.query.count()
    return render_template(
        "admin/dashboard.html",
        pending_count=pending_count,
        reset_count=reset_count,
        question_count=question_count,
    )


@admin_bp.route("/users")
@supervisor_required
def users():
    rows = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=rows)


@admin_bp.route("/users/new", methods=["GET", "POST"])
@supervisor_required
def user_new():
    form = UserForm()
    if request.method == "GET":
        form.status.data = "approved"
        form.is_active.data = True
        form.role.data = "user"
    if form.validate_on_submit():
        if not form.password.data:
            form.password.errors.append("Password is required for a new user.")
        elif User.query.filter_by(email=form.email.data.strip().lower()).first():
            form.email.errors.append("An account with that email already exists.")
        else:
            user = User(
                email=form.email.data.strip().lower(),
                nickname=resolve_nickname(form.nickname.data),
                real_name=(form.real_name.data or "").strip() or None,
                role=form.role.data,
                status=form.status.data,
                is_active=bool(form.is_active.data),
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash("User created.", "success")
            return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, title="Add user")


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@supervisor_required
def user_edit(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        clash = User.query.filter(User.email == email, User.id != user.id).first()
        if clash:
            form.email.errors.append("An account with that email already exists.")
        else:
            nick = resolve_nickname(form.nickname.data)
            nick_clash = User.query.filter(
                User.nickname == nick, User.id != user.id
            ).first()
            if nick_clash:
                form.nickname.errors.append("That nickname is already taken.")
            else:
                user.email = email
                user.nickname = nick
                user.real_name = (form.real_name.data or "").strip() or None
                user.role = form.role.data
                user.status = form.status.data
                user.is_active = bool(form.is_active.data)
                if form.password.data:
                    user.set_password(form.password.data)
                db.session.commit()
                flash("User updated.", "success")
                return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, title="Edit user", user=user)


@admin_bp.route("/users/pending", methods=["GET", "POST"])
@admin_required
def pending_users():
    if request.method == "POST":
        user = User.query.get_or_404(int(request.form["user_id"]))
        action = request.form.get("action")
        if action == "approve":
            user.status = "approved"
            flash(f"Approved {user.email}.", "success")
        elif action == "reject":
            user.status = "rejected"
            flash(f"Rejected {user.email}.", "info")
        db.session.commit()
        return redirect(url_for("admin.pending_users"))
    rows = User.query.filter_by(status="pending_approval").order_by(User.created_at).all()
    return render_template("admin/pending.html", users=rows)


@admin_bp.route("/reset-requests", methods=["GET", "POST"])
@admin_required
def reset_requests():
    issued_link = None
    if request.method == "POST":
        record = PasswordResetToken.query.get_or_404(int(request.form["request_id"]))
        raw = issue_reset_token(record, admin_id=current_user.id)
        issued_link = url_for("auth.reset_password", token=raw, _external=True)
        flash("Reset link issued. Copy it and send it to the user.", "success")
    open_requests = (
        PasswordResetToken.query.filter_by(used_at=None)
        .order_by(desc(PasswordResetToken.requested_at))
        .all()
    )
    return render_template(
        "admin/reset_requests.html", requests=open_requests, issued_link=issued_link
    )


@admin_bp.route("/questions")
@supervisor_required
def questions():
    rows = Question.query.order_by(desc(Question.updated_at)).all()
    return render_template("admin/questions.html", questions=rows)


@admin_bp.route("/links")
@admin_required
def links():
    rows = ResourceLink.query.order_by(ResourceLink.sort_order, ResourceLink.id).all()
    return render_template("admin/links.html", links=rows)


@admin_bp.route("/links/new", methods=["GET", "POST"])
@admin_required
def link_new():
    form = ResourceLinkForm()
    if form.validate_on_submit():
        db.session.add(
            ResourceLink(
                title=form.title.data.strip(),
                url=form.url.data.strip(),
                description=(form.description.data or "").strip() or None,
                sort_order=form.sort_order.data or 0,
                is_active=bool(form.is_active.data),
            )
        )
        db.session.commit()
        flash("Link added.", "success")
        return redirect(url_for("admin.links"))
    return render_template("admin/link_form.html", form=form, title="Add resource link")


@admin_bp.route("/links/<int:link_id>/edit", methods=["GET", "POST"])
@admin_required
def link_edit(link_id):
    link = ResourceLink.query.get_or_404(link_id)
    form = ResourceLinkForm(obj=link)
    if form.validate_on_submit():
        link.title = form.title.data.strip()
        link.url = form.url.data.strip()
        link.description = (form.description.data or "").strip() or None
        link.sort_order = form.sort_order.data or 0
        link.is_active = bool(form.is_active.data)
        db.session.commit()
        flash("Link updated.", "success")
        return redirect(url_for("admin.links"))
    return render_template("admin/link_form.html", form=form, title="Edit resource link")


@admin_bp.route("/links/<int:link_id>/delete", methods=["POST"])
@admin_required
def link_delete(link_id):
    link = ResourceLink.query.get_or_404(link_id)
    db.session.delete(link)
    db.session.commit()
    flash("Link deleted.", "info")
    return redirect(url_for("admin.links"))
