from flask import Flask, render_template
from flask_login import current_user

from app.bootstrap import bootstrap_first_admin, seed_default_resource_link
from app.config import Config
from app.extensions import csrf, db, login_manager, migrate
from app.models.resource_link import ResourceLink
from app.models.user import User


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=False)
    cfg = Config()
    app.config.from_object(cfg)
    app.config["FIRST_ADMIN"] = cfg.FIRST_ADMIN
    app.config["RESET_FIRST_ADMIN_PASSWORD"] = cfg.RESET_FIRST_ADMIN_PASSWORD
    app.config["SITE_TITLE"] = cfg.SITE_TITLE
    app.config["BACKDROP_IMAGE_URL"] = cfg.BACKDROP_IMAGE_URL

    if test_config:
        app.config.update(test_config)
        app.config["WTF_CSRF_ENABLED"] = test_config.get("WTF_CSRF_ENABLED", False)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app import models  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_globals():
        links = []
        try:
            links = (
                ResourceLink.query.filter_by(is_active=True)
                .order_by(ResourceLink.sort_order, ResourceLink.id)
                .all()
            )
        except Exception:
            links = []
        return {
            "site_title": app.config.get("SITE_TITLE") or "LWPL - Referee Forum",
            "backdrop_image_url": app.config.get("BACKDROP_IMAGE_URL") or "",
            "nav_resource_links": links,
            "current_user": current_user,
        }

    from app.blueprints.admin import admin_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.forum import forum_bp
    from app.blueprints.main import main_bp
    from app.cli import register_cli

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(forum_bp)
    app.register_blueprint(admin_bp)
    register_cli(app)

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    if not app.config.get("TESTING"):
        with app.app_context():
            try:
                from sqlalchemy import inspect as sa_inspect

                if sa_inspect(db.engine).has_table("users"):
                    bootstrap_first_admin()
                    seed_default_resource_link()
            except Exception as exc:
                app.logger.warning("Startup bootstrap skipped: %s", exc)

    return app
