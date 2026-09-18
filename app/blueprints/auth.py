from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.forms import (
    ChangePasswordForm,
    LoginForm,
    NicknameForm,
    RegisterForm,
    RequestResetForm,
    ResetPasswordForm,
)
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.nicknames import resolve_nickname
from app.tokens import load_reset_token

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data.strip().lower(),
            nickname=resolve_nickname(form.nickname.data),
            real_name=(form.real_name.data or "").strip() or None,
            role="user",
            status="pending_approval",
            is_active=True,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Your account is awaiting admin approval.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user is None or not user.check_password(form.password.data) or not user.can_login:
            flash("Invalid email or password", "danger")
            return render_template("auth/login.html", form=form)
        login_user(user, remember=form.remember.data)
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(url_for("main.home"))
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    nick_form = NicknameForm()
    pass_form = ChangePasswordForm()

    if request.method == "POST" and request.form.get("form_name") == "nickname":
        nick_form = NicknameForm(formdata=request.form)
        if nick_form.validate():
            new_nick = resolve_nickname(nick_form.nickname.data)
            clash = User.query.filter(
                User.nickname == new_nick, User.id != current_user.id
            ).first()
            if clash:
                flash("That nickname is already taken.", "danger")
            else:
                current_user.nickname = new_nick
                db.session.commit()
                flash("Nickname updated.", "success")
                return redirect(url_for("auth.profile"))
    elif request.method == "POST" and request.form.get("form_name") == "password":
        pass_form = ChangePasswordForm(formdata=request.form)
        if pass_form.validate():
            if not current_user.check_password(pass_form.current_password.data):
                flash("Current password is incorrect.", "danger")
            else:
                current_user.set_password(pass_form.new_password.data)
                db.session.commit()
                flash("Password changed.", "success")
                return redirect(url_for("auth.profile"))

    if request.method == "GET":
        nick_form.nickname.data = current_user.nickname
    return render_template(
        "auth/profile.html", nick_form=nick_form, pass_form=pass_form
    )


@auth_bp.route("/request-reset", methods=["GET", "POST"])
def request_reset():
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user:
            existing = PasswordResetToken.query.filter_by(
                user_id=user.id, used_at=None, token_hash=None
            ).first()
            if existing is None:
                db.session.add(PasswordResetToken(user_id=user.id))
                db.session.commit()
        flash(
            "If that email is registered, an admin will be asked to issue a reset link.",
            "info",
        )
        return redirect(url_for("auth.login"))
    return render_template("auth/request_reset.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    record = load_reset_token(token)
    if record is None:
        flash("That reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.login"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        record.user.set_password(form.password.data)
        from datetime import datetime, timezone

        record.used_at = datetime.now(timezone.utc)
        db.session.commit()
        flash("Your password has been updated. You can log in now.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form)
