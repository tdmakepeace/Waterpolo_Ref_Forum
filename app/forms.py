from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import (
    URL,
    DataRequired,
    Email,
    EqualTo,
    Length,
    Optional,
    ValidationError,
)

from app.models.user import User


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=8, max=128)]
    )
    confirm = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")],
    )
    nickname = StringField("Nickname (optional)", validators=[Optional(), Length(max=80)])
    real_name = StringField("Real name (optional, never shown publicly)", validators=[Optional(), Length(max=120)])

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("An account with that email already exists.")

    def validate_nickname(self, field):
        if field.data and User.query.filter_by(nickname=field.data.strip()).first():
            raise ValidationError("That nickname is already taken.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")


class NicknameForm(FlaskForm):
    nickname = StringField("Nickname", validators=[Optional(), Length(max=80)])


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField(
        "New password", validators=[DataRequired(), Length(min=8, max=128)]
    )
    confirm = PasswordField(
        "Confirm new password",
        validators=[DataRequired(), EqualTo("new_password", message="Passwords must match")],
    )


class RequestResetForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])


class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        "New password", validators=[DataRequired(), Length(min=8, max=128)]
    )
    confirm = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")],
    )


class QuestionForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    body = TextAreaField("Question", validators=[DataRequired(), Length(min=10)])


class ReplyForm(FlaskForm):
    body = TextAreaField("Reply", validators=[DataRequired(), Length(min=2)])


class UserForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[Optional(), Length(min=8, max=128)])
    nickname = StringField("Nickname", validators=[Optional(), Length(max=80)])
    real_name = StringField("Real name", validators=[Optional(), Length(max=120)])
    role = SelectField(
        "Role",
        choices=[("user", "User"), ("supervisor", "Supervisor"), ("admin", "Admin")],
        validators=[DataRequired()],
    )
    status = SelectField(
        "Status",
        choices=[
            ("pending_approval", "Pending approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        validators=[DataRequired()],
    )
    is_active = BooleanField("Active")


class ResourceLinkForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    url = StringField("URL", validators=[DataRequired(), URL(), Length(max=500)])
    description = TextAreaField("Description", validators=[Optional()])
    sort_order = IntegerField("Sort order", default=0)
    is_active = BooleanField("Active", default=True)
