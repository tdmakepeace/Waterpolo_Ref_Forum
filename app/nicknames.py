import secrets
import string

from app.models.user import User

ALPHABET = string.ascii_letters + string.digits


def generate_unique_nickname():
    for _ in range(50):
        candidate = "".join(secrets.choice(ALPHABET) for _ in range(8))
        if User.query.filter_by(nickname=candidate).first() is None:
            return candidate
    raise RuntimeError("Could not generate a unique nickname")


def resolve_nickname(nickname):
    cleaned = (nickname or "").strip()
    if cleaned:
        return cleaned
    return generate_unique_nickname()
