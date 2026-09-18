from flask import current_app

from app.extensions import db
from app.models.resource_link import ResourceLink
from app.models.user import User
from app.nicknames import resolve_nickname
from app.resource_import import import_resource_links


def bootstrap_first_admin():
    cfg = current_app.config.get("FIRST_ADMIN") or {}
    email = (cfg.get("email") or "").strip().lower()
    password = cfg.get("password")
    if not email or not password:
        current_app.logger.warning("first_admin email/password missing from config")
        return

    user = User.query.filter_by(is_bootstrap_admin=True).first()
    if user is None:
        user = User.query.filter_by(email=email).first()

    if user is None:
        nickname = resolve_nickname(cfg.get("nickname"))
        user = User(
            email=email,
            nickname=nickname,
            role="admin",
            status="approved",
            is_active=True,
            is_bootstrap_admin=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        current_app.logger.info("Created bootstrap admin %s", email)
        return

    user.is_bootstrap_admin = True
    user.email = email
    user.role = "admin"
    user.status = "approved"
    user.is_active = True
    if current_app.config.get("RESET_FIRST_ADMIN_PASSWORD"):
        user.set_password(password)
        current_app.logger.info("Reset bootstrap admin password from config")
    db.session.commit()


def seed_default_resource_link():
    """Seed the bundled catalog only when the resources table is empty.

    Existing deployments keep their current links. To add or refresh the
    referee catalog, run `python scripts/import_resource_links.py`.
    """
    if ResourceLink.query.first() is not None:
        return
    import_resource_links()
