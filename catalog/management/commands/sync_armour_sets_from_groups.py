from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from catalog.models import ArmourSet, Product, ProductGroup


class Command(BaseCommand):
    help = "Sync ArmourSet records and Product.armour_set from ProductGroup (armour_set)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB.")
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing Product.armour_set assignments and ArmourSet fields.",
        )

    def handle(self, *args, **opts):
        dry_run = bool(opts["dry_run"])
        overwrite = bool(opts["overwrite"])

        groups = ProductGroup.objects.filter(group_type=ProductGroup.GroupType.ARMOUR_SET)
        if not groups.exists():
            self.stdout.write(self.style.WARNING("No ProductGroup armour sets found. Run build_armour_sets first."))
            return

        created_sets = 0
        updated_sets = 0
        assigned = 0
        skipped = 0

        @transaction.atomic
        def apply():
            nonlocal created_sets, updated_sets, assigned, skipped

            for g in groups:
                set_name = g.name
                set_slug = g.slug or slugify(set_name)

                armour_set, was_created = ArmourSet.objects.get_or_create(
                    name=set_name,
                    defaults={"slug": set_slug},
                )

                if was_created:
                    created_sets += 1

                # Set hero_image from group's primary_product image if available
                hero_asset = None
                if g.primary_product:
                    primary_pi = g.primary_product.images.filter(is_primary=True).select_related("asset").first()
                    if primary_pi and primary_pi.asset:
                        hero_asset = primary_pi.asset

                changed = False
                if overwrite:
                    if armour_set.slug != set_slug:
                        armour_set.slug = set_slug
                        changed = True
                    if hero_asset and armour_set.hero_image_id != hero_asset.id:
                        armour_set.hero_image = hero_asset
                        changed = True
                else:
                    # Fill missing hero_image only
                    if hero_asset and not armour_set.hero_image_id:
                        armour_set.hero_image = hero_asset
                        changed = True

                if changed and not dry_run:
                    armour_set.save()
                    updated_sets += 1

                # Assign products to this set
                products = list(g.products.all())
                for p in products:
                    if not overwrite and p.armour_set_id and p.armour_set_id != armour_set.id:
                        skipped += 1
                        continue

                    if dry_run:
                        assigned += 1
                        continue

                    if p.armour_set_id != armour_set.id:
                        p.armour_set = armour_set
                        p.save(update_fields=["armour_set"])
                        assigned += 1

        apply()

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no DB changes were made."))

        self.stdout.write(self.style.SUCCESS("Sync complete."))
        self.stdout.write(f"Groups scanned: {groups.count()}")
        self.stdout.write(f"ArmourSets created: {created_sets}")
        self.stdout.write(f"ArmourSets updated: {updated_sets}")
        self.stdout.write(f"Products assigned: {assigned}")
        self.stdout.write(f"Products skipped (already in another set): {skipped}")
