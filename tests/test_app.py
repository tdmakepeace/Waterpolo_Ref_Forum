import pytest

from app import create_app
from app.extensions import db
from app.models.question import STATUS_CLOSED, Question
from app.models.reply import Reply
from app.models.user import User
from app.models.vote import Vote, refresh_question_score
from app.nicknames import generate_unique_nickname


@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "test.db"
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path.as_posix()}",
            "SECRET_KEY": "test-secret",
            "WTF_CSRF_ENABLED": False,
            "FIRST_ADMIN": {},
            "RESET_FIRST_ADMIN_PASSWORD": False,
        }
    )
    with application.app_context():
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _make_user(
    email,
    password="password12",
    role="user",
    status="approved",
    nickname=None,
    **kwargs,
):
    user = User(
        email=email,
        nickname=nickname or email.split("@")[0],
        role=role,
        status=status,
        is_active=True,
        **kwargs,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def test_pending_user_cannot_login(app, client):
    with app.app_context():
        _make_user("pending@example.com", status="pending_approval", nickname="pend1")
    response = client.post(
        "/login",
        data={"email": "pending@example.com", "password": "password12"},
        follow_redirects=True,
    )
    assert b"Invalid email or password" in response.data


def test_blank_nickname_is_random(app, client):
    client.post(
        "/register",
        data={
            "email": "newref@example.com",
            "password": "password12",
            "confirm": "password12",
            "nickname": "",
        },
        follow_redirects=True,
    )
    with app.app_context():
        user = User.query.filter_by(email="newref@example.com").first()
        assert user is not None
        assert user.nickname
        assert len(user.nickname) == 8
        assert user.status == "pending_approval"


def test_approved_user_posts_nickname_only(app, client):
    with app.app_context():
        user = _make_user(
            "ref@example.com", nickname="Whistle1", real_name="Secret Name"
        )
        user_id = user.id
    client.post(
        "/login",
        data={"email": "ref@example.com", "password": "password12"},
        follow_redirects=True,
    )
    client.post(
        "/questions/new",
        data={"title": "Exclusion at 6m", "body": "Is this a penalty or exclusion?"},
        follow_redirects=True,
    )
    listing = client.get("/questions?tab=open")
    assert b"Whistle1" in listing.data
    assert b"Secret Name" not in listing.data
    assert b"ref@example.com" not in listing.data
    with app.app_context():
        assert User.query.get(user_id).real_name == "Secret Name"


def test_closed_question_rejects_reply(app, client):
    with app.app_context():
        user = _make_user("owner@example.com", nickname="Owner1")
        q = Question(
            user_id=user.id,
            author_nickname=user.nickname,
            title="Closed thread",
            body="Body of the closed question here.",
            status=STATUS_CLOSED,
        )
        db.session.add(q)
        db.session.commit()
        qid = q.id
    client.post("/login", data={"email": "owner@example.com", "password": "password12"})
    response = client.post(
        f"/questions/{qid}",
        data={"body": "Should not post"},
        follow_redirects=True,
    )
    assert b"closed to new replies" in response.data
    with app.app_context():
        assert Reply.query.filter_by(question_id=qid).count() == 0


def test_hidden_visibility(app, client):
    with app.app_context():
        author = _make_user("author@example.com", nickname="Author1")
        other = _make_user("other@example.com", nickname="Other1")
        staff = _make_user("sup@example.com", nickname="Sup1", role="supervisor")
        q = Question(
            user_id=author.id,
            author_nickname=author.nickname,
            title="Hidden thread",
            body="Sensitive discussion that should be hidden from most users.",
            is_hidden=True,
        )
        db.session.add(q)
        db.session.commit()
        qid = q.id
    assert client.get(f"/questions/{qid}").status_code == 404
    client.post("/login", data={"email": "other@example.com", "password": "password12"})
    assert client.get(f"/questions/{qid}").status_code == 404
    client.get("/logout")
    client.post("/login", data={"email": "author@example.com", "password": "password12"})
    assert client.get(f"/questions/{qid}").status_code == 200
    client.get("/logout")
    client.post("/login", data={"email": "sup@example.com", "password": "password12"})
    assert client.get(f"/questions/{qid}").status_code == 200


def test_vote_replace_not_stack(app):
    with app.app_context():
        user = _make_user("voter@example.com", nickname="Voter1")
        q = Question(
            user_id=user.id,
            author_nickname=user.nickname,
            title="Vote me",
            body="Please vote this question up or down accordingly.",
        )
        db.session.add(q)
        db.session.commit()
        db.session.add(Vote(user_id=user.id, question_id=q.id, value=1))
        db.session.flush()
        refresh_question_score(q)
        db.session.commit()
        vote = Vote.query.filter_by(user_id=user.id, question_id=q.id).first()
        vote.value = -1
        db.session.flush()
        refresh_question_score(q)
        db.session.commit()
        assert q.score == -1
        assert Vote.query.filter_by(question_id=q.id).count() == 1


def test_user_forbidden_on_admin(app, client):
    with app.app_context():
        _make_user("user@example.com", nickname="User1")
    client.post("/login", data={"email": "user@example.com", "password": "password12"})
    assert client.get("/admin/").status_code == 403
    assert client.get("/admin/users").status_code == 403


def test_supervisor_cannot_use_admin_only_routes(app, client):
    with app.app_context():
        _make_user("sup@example.com", nickname="Sup2", role="supervisor")
    client.post("/login", data={"email": "sup@example.com", "password": "password12"})
    assert client.get("/admin/users").status_code == 200
    assert client.get("/admin/users/pending").status_code == 403
    assert client.get("/admin/reset-requests").status_code == 403
    assert client.get("/admin/links").status_code == 403


def test_admin_can_access_admin_only_routes(app, client):
    with app.app_context():
        _make_user("admin@example.com", nickname="Admin1", role="admin")
    client.post("/login", data={"email": "admin@example.com", "password": "password12"})
    assert client.get("/admin/users/pending").status_code == 200
    assert client.get("/admin/reset-requests").status_code == 200
    assert client.get("/admin/links").status_code == 200


def test_generate_unique_nickname(app):
    with app.app_context():
        nick = generate_unique_nickname()
        assert len(nick) == 8


def test_import_resource_links_adds_missing_and_skips_existing(app, tmp_path):
    catalog = tmp_path / "links.json"
    catalog.write_text(
        '{"links":['
        '{"title":"Rules A","url":"https://example.com/a","sort_order":1},'
        '{"title":"Rules B","url":"https://example.com/b","description":"B","sort_order":2}'
        "]}",
        encoding="utf-8",
    )
    from app.models.resource_link import ResourceLink
    from app.resource_import import import_resource_links

    with app.app_context():
        db.session.add(
            ResourceLink(
                title="Old A",
                url="https://example.com/a",
                description="keep me",
                sort_order=9,
                is_active=True,
            )
        )
        db.session.commit()
        skipped = import_resource_links(path=catalog)
        assert skipped["added"] == 1
        assert skipped["updated"] == 0
        assert skipped["skipped"] == 1
        assert ResourceLink.query.count() == 2
        original = ResourceLink.query.filter_by(url="https://example.com/a").one()
        assert original.title == "Old A"
        assert original.description == "keep me"

        refreshed = import_resource_links(path=catalog, update=True)
        assert refreshed["added"] == 0
        assert refreshed["updated"] == 2
        original = ResourceLink.query.filter_by(url="https://example.com/a").one()
        assert original.title == "Rules A"
        assert original.sort_order == 1


def test_import_resource_links_dry_run_does_not_write(app, tmp_path):
    catalog = tmp_path / "links.json"
    catalog.write_text(
        '{"links":[{"title":"Rules C","url":"https://example.com/c","sort_order":3}]}',
        encoding="utf-8",
    )
    from app.models.resource_link import ResourceLink
    from app.resource_import import import_resource_links

    with app.app_context():
        result = import_resource_links(path=catalog, dry_run=True)
        assert result["added"] == 1
        assert result["dry_run"] is True
        assert ResourceLink.query.count() == 0
