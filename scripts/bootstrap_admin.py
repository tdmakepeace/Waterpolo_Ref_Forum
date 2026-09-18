"""CLI helper — the web process also runs this on startup via create_app()."""
from app import create_app
from app.bootstrap import bootstrap_first_admin, seed_default_resource_link


def main():
    app = create_app()
    with app.app_context():
        bootstrap_first_admin()
        seed_default_resource_link()
        print("Bootstrap complete.")


if __name__ == "__main__":
    main()
