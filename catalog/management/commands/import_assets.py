import hashlib
import os
import re
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Asset


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def slugish(value: str) -> str:
    """
    Make a safe identifier from filenames:
    - lowercase
    - spaces -> hyphens
    - strip odd chars
    """
    value = value.strip().lower().replace(" ", "-")
    value = re.sub(r"[^a-z0-9\-_\.]+", "", value)
    value = re.sub(r"-{2,}", "-", value)
    return value


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class Command(BaseCommand):
    help = "Bulk import image assets into the Asset model."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            required=True,
            help=r'Path to asset library folder, e.g. "C:\Users\tomgo\Documents\ashen-assets"',
        )
        parser.add_argument(
            "--use-hash-id",
            action="store_true",
            help="Use SHA1(file) as asset_id instead of filename stem (best if filenames may collide).",
        )
        parser.add_argument(
            "--source-label",
            default="external-library",
            help="Value stored in Asset.source (default: external-library).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Scan and report without creating records.",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="If an Asset already exists for asset_id, update its image/title/source.",
        )

    def handle(self, *args, **options):
        source = Path(options["source"]).expanduser().resolve()
        if not source.exists() or not source.is_dir():
            raise CommandError(f"Source folder not found or not a directory: {source}")

        use_hash_id = options["use_hash_id"]
        dry_run = options["dry_run"]
        update_existing = options["update_existing"]
        source_label = options["source_label"]

        # Find files
        files = []
        for p in source.rglob("*"):
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                files.append(p)

        if not files:
            self.stdout.write(self.style.WARNING("No image files found."))
            return

        created = 0
        updated = 0
        skipped = 0
        errors = 0

        self.stdout.write(f"Found {len(files)} image(s) under: {source}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN enabled — no DB changes will be made."))

        @transaction.atomic
        def process_all():
            nonlocal created, updated, skipped, errors

            for path in files:
                try:
                    rel = path.relative_to(source)

                    # Top-level folder becomes a useful source tag (weapons/shields/armour/etc.)
                    top_folder = rel.parts[0] if len(rel.parts) > 1 else "misc"

                    # asset_id: filename-based by default (easy to reason about)
                    # Use --use-hash-id if you have collisions.
                    filename_stem = slugish(path.stem)
                    if use_hash_id:
                        asset_id = sha1_file(path)[:16]
                    else:
                        asset_id = filename_stem

                    title = path.stem.replace("_", " ").replace("-", " ").strip().title()
                    source_value = f"{source_label}:{top_folder}"

                    existing = Asset.objects.filter(asset_id=asset_id).first()
                    if existing and not update_existing:
                        skipped += 1
                        continue

                    # Preserve the extension; normalise filename
                    safe_filename = slugish(path.name)
                    if not safe_filename.lower().endswith(path.suffix.lower()):
                        safe_filename = f"{safe_filename}{path.suffix.lower()}"

                    # Store in MEDIA_ROOT under /assets/<top_folder>/...
                    dest_name = os.path.join("assets", top_folder, safe_filename)

                    if dry_run:
                        if existing:
                            updated += 1
                        else:
                            created += 1
                        continue

                    obj = existing or Asset(asset_id=asset_id)
                    obj.title = title
                    obj.source = source_value

                    with path.open("rb") as f:
                        obj.image.save(dest_name, File(f), save=False)

                    obj.save()

                    if existing:
                        updated += 1
                    else:
                        created += 1

                except Exception as e:
                    errors += 1
                    self.stderr.write(self.style.ERROR(f"Error importing {path}: {e}"))

        process_all()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Import complete."))
        self.stdout.write(f"Created: {created}")
        self.stdout.write(f"Updated: {updated}")
        self.stdout.write(f"Skipped: {skipped}")
        self.stdout.write(f"Errors:  {errors}")

