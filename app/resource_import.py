import json
from pathlib import Path

from app.extensions import db
from app.models.resource_link import ResourceLink

DEFAULT_CATALOG = Path(__file__).resolve().parent.parent / "data" / "resource_links.json"


def load_resource_link_specs(path=None):
    catalog = Path(path) if path else DEFAULT_CATALOG
    payload = json.loads(catalog.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        rows = payload.get("links")
    else:
        rows = payload
    if not isinstance(rows, list):
        raise ValueError("Resource catalog must be a list or an object with a 'links' array.")

    specs = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Link {index} must be an object.")
        title = (row.get("title") or "").strip()
        url = (row.get("url") or "").strip()
        if not title or not url:
            raise ValueError(f"Link {index} needs both title and url.")
        specs.append(
            {
                "title": title[:200],
                "url": url[:500],
                "description": (row.get("description") or "").strip() or None,
                "sort_order": int(row.get("sort_order") or 0),
                "is_active": bool(row.get("is_active", True)),
            }
        )
    by_url = {spec["url"]: spec for spec in specs}
    return catalog, list(by_url.values())


def import_resource_links(path=None, update=False, dry_run=False):
    catalog, specs = load_resource_link_specs(path)
    existing_by_url = {link.url: link for link in ResourceLink.query.all()}
    added = updated = skipped = 0

    for spec in specs:
        current = existing_by_url.get(spec["url"])
        if current is None:
            db.session.add(
                ResourceLink(
                    title=spec["title"],
                    url=spec["url"],
                    description=spec["description"],
                    sort_order=spec["sort_order"],
                    is_active=spec["is_active"],
                )
            )
            added += 1
            continue
        if not update:
            skipped += 1
            continue
        current.title = spec["title"]
        current.description = spec["description"]
        current.sort_order = spec["sort_order"]
        updated += 1

    if dry_run:
        db.session.rollback()
    elif added or updated:
        db.session.commit()
    else:
        db.session.rollback()

    return {
        "file": str(catalog),
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "dry_run": dry_run,
    }
