from flask import Blueprint, render_template

from app.blueprints.forum import question_list_context
from app.models.resource_link import ResourceLink

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    ctx = question_list_context()
    if ctx["tab"] == "hidden":
        from flask_login import current_user
        from flask import abort

        if not current_user.is_authenticated:
            abort(404)
    return render_template("forum/list.html", is_home=True, **ctx)


@main_bp.route("/resources")
def resources():
    links = (
        ResourceLink.query.filter_by(is_active=True)
        .order_by(ResourceLink.sort_order, ResourceLink.id)
        .all()
    )
    return render_template("resources.html", links=links)
