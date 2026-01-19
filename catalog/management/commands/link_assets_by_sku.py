import re
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Asset, Product, ProductImage


def norm_key(value: str) -> str:
    """
    Normalise SKU / asset_id to a comparable key.
    Example:
      "menu-knowledge 10000" -> "MENU_KNOWLEDGE_10000"
    """
    value = (value or "").strip().upper()
    value = value.replace("-", "_").replace(" ", "_")
    value = re.sub(r"[^A-Z0-9_]+", "", value)
    value = re.sub(r"_+", "_", value)
    return value


class Command(BaseCommand):
    help = "Link Asset images to Products by matching Asset.asset_id to Product.sku (normalised)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would happen without writing to DB.",
        )
        parser.add_argument(
            "--source-folder",
            default="",
            help="Optional: only use assets where Asset.source ends with this folder (e.g. weapons, armour).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Optional: limit number of products to link (useful for testing).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        source_folder = options["source_folder"].strip().lower()
        limit = options["limit"]

        products = list(Product.objects.all())
        if not products:
            self.stdout.write(self.style.WARNING("No products found. Nothing to link."))
            return

        product_by_key = {}
        for p in products:
            product_by_key[norm_key(p.sku)] = p

        assets_qs = Asset.objects.all()
        if source_folder:
            assets_qs = assets_qs.filter(source__iendswith=f":{source_folder}")

        assets = list(assets_qs)
        if not assets:
            self.stdout.write(self.style.WARNING("No assets found for given criteria."))
            return

        # Group assets by key
        assets_by_key = defaultdict(list)
        for a in assets:
            assets_by_key[norm_key(a.asset_id)].append(a)

        to_create = []
        already_linked = 0
        unmatched_assets = 0
        products_linked = 0

        # Track per product which assets to link
        for key, group in assets_by_key.items():
            product = product_by_key.get(key)
            if not product:
                unmatched_assets += len(group)
                continue

            # Optionally limit how many products we link
            if limit and products_linked >= limit:
                break

            # Existing links for this product
            existing_asset_ids = set(
                ProductImage.objects.filter(product=product).values_list("asset_id", flat=True)
            )

            # Sort group deterministically (by asset_id)
            group_sorted = sorted(group, key=lambda x: x.asset_id)

            # Determine next sort order
            current_max_sort = (
                ProductImage.objects.filter(product=product).order_by("-sort_order").values_list("sort_order", flat=True).first()
            )
            next_sort = (current_max_sort + 1) if current_max_sort is not None else 0

            # If product has no images yet, first new image becomes primary
            has_any_images = ProductImage.objects.filter(product=product).exists()
            primary_set = has_any_images

            created_for_product = 0

            for asset in group_sorted:
                if asset.id in existing_asset_ids:
                    already_linked += 1
                    continue

                pi = ProductImage(
                    product=product,
                    asset=asset,
                    alt_text=product.name,
                    sort_order=next_sort,
                    is_primary=(not primary_set),
                )
                if not primary_set:
                    primary_set = True

                to_create.append(pi)
                next_sort += 1
                created_for_product += 1

            if created_for_product:
                products_linked += 1

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no DB changes will be made."))
            self.stdout.write(f"Products total: {len(products)}")
            self.stdout.write(f"Assets scanned: {len(assets)}")
            self.stdout.write(f"Unmatched assets: {unmatched_assets}")
            self.stdout.write(f"Already linked (skipped): {already_linked}")
            self.stdout.write(f"New ProductImage links: {len(to_create)}")
            self.stdout.write(f"Products receiving new links: {products_linked}")
            return

        with transaction.atomic():
            ProductImage.objects.bulk_create(to_create, batch_size=500)

        self.stdout.write(self.style.SUCCESS("Linking complete."))
        self.stdout.write(f"New ProductImage links created: {len(to_create)}")
        self.stdout.write(f"Unmatched assets: {unmatched_assets}")
        self.stdout.write(f"Already linked (skipped): {already_linked}")
        self.stdout.write(f"Products updated: {products_linked}")
