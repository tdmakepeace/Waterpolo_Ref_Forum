from flask import Blueprint, render_template, request

from app.blueprints.forum import listing_query, _vote_map
from app.models.resource_link import ResourceLink

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    tab = request.args.get("tab", "open")
    if tab not in ("open", "closed", "hidden"):
        tab = "open"
    if tab == "hidden":
        from flask_login import current_user
        from flask import abort

        if not current_user.is_authenticated:
            abort(404)
    questions = listing_query(tab).all()
    return render_template(
        "forum/list.html",
        questions=questions,
        tab=tab,
        votes_by_question=_vote_map(questions),
        is_home=True,
    )


@main_bp.route("/resources")
def resources():
    links = (
        ResourceLink.query.filter_by(is_active=True)
        .order_by(ResourceLink.sort_order, ResourceLink.id)
        .all()
    )
    return render_template("resources.html", links=links)
