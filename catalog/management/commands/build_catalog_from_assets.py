import re

from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Asset, Product, ProductImage


def norm_sku(value: str) -> str:
    value = (value or "").strip().upper()
    value = value.replace("-", "_").replace(" ", "_")
    value = re.sub(r"[^A-Z0-9_]+", "", value)
    value = re.sub(r"_+", "_", value)
    return value


def category_from_source(asset: Asset) -> str:
    folder = (asset.source or "").split(":")[-1].strip().lower()

    mapping = {
        "weapons": Product.Category.WEAPON,
        "weapon": Product.Category.WEAPON,
        "shields": Product.Category.SHIELD,
        "shield": Product.Category.SHIELD,
        "armour": Product.Category.ARMOUR,
        "armor": Product.Category.ARMOUR,
        "relics": Product.Category.RELIC,
        "relic": Product.Category.RELIC,
        "consumables": Product.Category.CONSUMABLE,
        "consumable": Product.Category.CONSUMABLE,
        "spells": Product.Category.SPELL,
        "spell": Product.Category.SPELL,
    }
    return mapping.get(folder, Product.Category.RELIC)


class Command(BaseCommand):
    help = "Create draft Products (1 per Asset) using Asset.asset_id as SKU and Asset.title as name, and link images."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB.")
        parser.add_argument("--limit", type=int, default=0, help="Limit number of assets processed (testing).")
        parser.add_argument("--price", type=int, default=999, help="Default price in pence (e.g. 999 = £9.99).")
        parser.add_argument("--stock", type=int, default=0, help="Default stock quantity.")
        parser.add_argument(
            "--publish",
            action="store_true",
            help="If set, products are created as is_active=True (default draft False).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]
        default_price = options["price"]
        default_stock = options["stock"]
        publish = options["publish"]

        assets_qs = Asset.objects.order_by("id")
        if limit:
            assets_qs = assets_qs[:limit]

        created_products = 0
        created_links = 0
        skipped_existing = 0
        skipped_no_sku = 0

        for asset in assets_qs:
            sku = norm_sku(asset.asset_id)
            if not sku:
                skipped_no_sku += 1
                continue

            existing = Product.objects.filter(sku=sku).first()
            if existing:
                skipped_existing += 1
                if publish:
                    existing.is_active = True
                existing.stock_qty = default_stock
                existing.price_pence = default_price
                existing.save(update_fields=["is_active", "stock_qty", "price_pence"])
                continue


            name = (asset.title or "").strip() or sku.replace("_", " ").title()
            category = category_from_source(asset)

            if dry_run:
                created_products += 1
                created_links += 1
                continue

            with transaction.atomic():
                product = Product.objects.create(
                    sku=sku,
                    name=name,
                    category=category,
                    rarity=Product.Rarity.COMMON,
                    price_pence=default_price,
                    stock_qty=default_stock,
                    short_description="A relic catalogued from the Ashen archives.",
                    description=(
                        "A fragment of a forgotten age, recorded by the Emporium. "
                        "Its true purpose is veiled, but its presence is undeniable."
                    ),
                    is_active=publish,
                )

                ProductImage.objects.create(
                    product=product,
                    asset=asset,
                    alt_text=name,
                    sort_order=0,
                    is_primary=True,
                )

                created_products += 1
                created_links += 1

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no DB changes will be made."))

        self.stdout.write(self.style.SUCCESS("Build complete."))
        self.stdout.write(f"Products created: {created_products}")
        self.stdout.write(f"ProductImage links created: {created_links}")
        self.stdout.write(f"Skipped (product already existed): {skipped_existing}")
        self.stdout.write(f"Skipped (no SKU): {skipped_no_sku}")
