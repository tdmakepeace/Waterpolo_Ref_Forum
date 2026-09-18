import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models.password_reset import PasswordResetToken


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_reset_token(record, admin_id, hours=24):
    raw = secrets.token_urlsafe(32)
    record.token_hash = hash_token(raw)
    record.expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
    record.issued_by_admin_id = admin_id
    db.session.commit()
    return raw


def load_reset_token(raw_token):
    if not raw_token:
        return None
    digest = hash_token(raw_token)
    record = PasswordResetToken.query.filter_by(token_hash=digest, used_at=None).first()
    if record is None or record.expires_at is None:
        return None
    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        return None
    return record
