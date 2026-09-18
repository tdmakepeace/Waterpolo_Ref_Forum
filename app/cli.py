import click

from app.resource_import import import_resource_links


def register_cli(app):
    @app.cli.command("import-resource-links")
    @click.option(
        "--file",
        "file_path",
        default=None,
        help="JSON catalog path (default: data/resource_links.json)",
    )
    @click.option(
        "--update",
        is_flag=True,
        help="Update title, description and sort order when the URL already exists",
    )
    @click.option(
        "--dry-run",
        is_flag=True,
        help="Show what would change without writing to the database",
    )
    def import_resource_links_command(file_path, update, dry_run):
        result = import_resource_links(path=file_path, update=update, dry_run=dry_run)
        prefix = "Dry run: " if result["dry_run"] else ""
        click.echo(f"{prefix}Imported resource links from {result['file']}")
        click.echo(f"  added:   {result['added']}")
        click.echo(f"  updated: {result['updated']}")
        click.echo(f"  skipped: {result['skipped']}")
