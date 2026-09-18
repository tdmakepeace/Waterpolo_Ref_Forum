"""Import referee resource links into an existing deployment.

Default: insert catalog URLs that are not already present.
Use --update to refresh title, description and sort order for matching URLs.
Existing custom links (different URLs) are left alone. --update does not
change is_active, so a hidden catalog link stays hidden.

Docker (existing deployment):

    docker compose exec web python scripts/import_resource_links.py --dry-run
    docker compose exec web python scripts/import_resource_links.py
    docker compose exec web python scripts/import_resource_links.py --update

Local Flask:

    python scripts/import_resource_links.py --file data/resource_links.json
"""
import argparse
import sys
from pathlib import Path

# `python scripts/foo.py` puts scripts/ on sys.path, not the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.resource_import import import_resource_links


def main(argv=None):
    parser = argparse.ArgumentParser(description="Import resource links into the forum database.")
    parser.add_argument(
        "--file",
        dest="file_path",
        default=None,
        help="JSON catalog path (default: data/resource_links.json)",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update title, description and sort order when the URL already exists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing to the database",
    )
    args = parser.parse_args(argv)

    app = create_app()
    with app.app_context():
        result = import_resource_links(
            path=args.file_path,
            update=args.update,
            dry_run=args.dry_run,
        )

    prefix = "Dry run: " if result["dry_run"] else ""
    print(f"{prefix}Imported resource links from {result['file']}")
    print(f"  added:   {result['added']}")
    print(f"  updated: {result['updated']}")
    print(f"  skipped: {result['skipped']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
