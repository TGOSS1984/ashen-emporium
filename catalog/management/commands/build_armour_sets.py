import csv
import re
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Product, ProductGroup


ALTERED_RE = re.compile(r"\s*\(altered\)\s*$", re.IGNORECASE)


# Words that typically indicate a "piece" (we remove these to find the set name)
PIECE_WORDS = [
    "helm", "helmet", "hood", "hat", "mask", "crown",
    "robe", "armor", "armour", "chest", "cuirass", "garb", "coat",
    "gauntlets", "gloves", "bracers", "manchettes",
    "greaves", "boots", "trousers", "leggings", "legwraps",
    "headband",
]


PRIMARY_PREFER = [
    "robe", "armor", "armour", "cuirass", "chest", "garb", "coat",
]


def norm_spaces(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s


def clean_name(raw: str) -> str:
    """
    Normalise product names:
    - replace _s with 's (your filenames use Alberich_s)
    - replace underscores with spaces
    - remove trailing (Altered)
    """
    s = (raw or "").strip()
    s = s.replace("_s", "'s").replace("_S", "'s")
    s = s.replace("_", " ")
    s = ALTERED_RE.sub("", s)
    return norm_spaces(s)


def derive_set_name(product_name: str) -> str:
    """
    Derive a set name from a product name.

    Examples:
      "Alberich's Robe" -> "Alberich's Set"
      "All-Knowing Helm" -> "All-Knowing Set"
      "Banished Knight Greaves" -> "Banished Knight Set"
    """
    s = clean_name(product_name)

    # Remove piece word at end if present
    lower = s.lower()
    for w in PIECE_WORDS:
        if lower.endswith(" " + w):
            s = s[: -(len(w) + 1)]
            s = s.strip()
            break

    # If nothing left, fallback to original cleaned
    if not s:
        s = clean_name(product_name)

    return f"{s} Set"


def choose_primary(products):
    """
    Choose primary piece:
    Prefer robe/armor/chest-like names; otherwise the first.
    """
    def score(p: Product) -> int:
        name = clean_name(p.name).lower()
        for i, kw in enumerate(PRIMARY_PREFER):
            if kw in name:
                return 100 - i
        return 0

    return max(products, key=score)


class Command(BaseCommand):
    help = "Auto-build armour sets (ProductGroup) from armour product names."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB.")
        parser.add_argument(
            "--report",
            default="reports/armour_set_build_report.csv",
            help="CSV report path (default: reports/armour_set_build_report.csv).",
        )
        parser.add_argument(
            "--min-size",
            type=int,
            default=2,
            help="Minimum number of products required to create a set (default: 2).",
        )

    def handle(self, *args, **opts):
        dry_run = bool(opts["dry_run"])
        report_path = Path(opts["report"])
        min_size = int(opts["min_size"])

        armour_products = list(Product.objects.filter(category=Product.Category.ARMOUR))
        if not armour_products:
            self.stdout.write(self.style.WARNING("No armour products found."))
            return

        # Group products by derived set name
        groups = defaultdict(list)
        for p in armour_products:
            set_name = derive_set_name(p.name)
            groups[set_name].append(p)

        # Only keep meaningful groups
        groups = {k: v for k, v in groups.items() if len(v) >= min_size}

        # --- Generic shared-piece handling ---
        # If we have a base group "X Set" and variant groups like "X Y Set", then
        # distribute the base group's products into each variant and remove the base group.
        #
        # Example:
        #   "Crucible Set" -> products: [Gauntlets, Greaves]
        #   "Crucible Axe Set" -> products: [Axe Armor, Axe Helm]
        #   "Crucible Tree Set" -> products: [Tree Armor, Tree Helm]
        #
        # After this, both Axe/Tree sets get Gauntlets/Greaves and "Crucible Set" disappears.

        def stem(set_name: str) -> str:
            return set_name[:-4] if set_name.endswith(" Set") else set_name

        # Build list of set names (stems) for comparison
        set_names = list(groups.keys())
        stems = [stem(n) for n in set_names]

        # Identify base stems that have variants (variants are any stem starting with base + " ")
        base_to_variants = defaultdict(list)
        for base in stems:
            for candidate in stems:
                if candidate != base and candidate.startswith(base + " "):
                    base_to_variants[base].append(candidate)

        # Distribute base group products into all variants and remove base group from groups dict
        for base, variants in base_to_variants.items():
            base_set_name = f"{base} Set"
            if base_set_name not in groups:
                continue  # nothing to distribute

            # Only treat as "shared base" if there is at least 1 variant group
            if not variants:
                continue

            shared_products = groups[base_set_name]

            for var in variants:
                var_set_name = f"{var} Set"
                if var_set_name in groups:
                    groups[var_set_name].extend(shared_products)

            # Remove the base set to avoid creating the unwanted third group
            groups.pop(base_set_name, None)

        # De-duplicate products inside each group after distribution
        for k, plist in groups.items():
            seen = set()
            deduped = []
            for p in plist:
                if p.id in seen:
                    continue
                seen.add(p.id)
                deduped.append(p)
            groups[k] = deduped



        report_path.parent.mkdir(parents=True, exist_ok=True)
        rows = []

        created = 0
        updated = 0
        skipped = 0

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no DB changes will be made."))

        @transaction.atomic
        def apply():
            nonlocal created, updated, skipped

            for set_name, products in sorted(groups.items(), key=lambda x: x[0].lower()):
                primary = choose_primary(products)

                if dry_run:
                    rows.append([set_name, len(products), primary.sku, primary.name, "DRY_RUN"])
                    continue

                group, was_created = ProductGroup.objects.get_or_create(
                    name=set_name,
                    defaults={
                        "group_type": ProductGroup.GroupType.ARMOUR_SET,
                        "category": Product.Category.ARMOUR,
                        "primary_product": primary,
                    },
                )

                # Update primary if missing or if we found a better one
                changed = False
                if group.category != Product.Category.ARMOUR:
                    group.category = Product.Category.ARMOUR
                    changed = True
                if group.group_type != ProductGroup.GroupType.ARMOUR_SET:
                    group.group_type = ProductGroup.GroupType.ARMOUR_SET
                    changed = True
                if group.primary_product_id != primary.id:
                    group.primary_product = primary
                    changed = True

                if changed:
                    group.save()
                    updated += 1

                if was_created:
                    created += 1

                # Attach products (idempotent)
                group.products.set(products)

                rows.append([set_name, len(products), primary.sku, primary.name, "CREATED" if was_created else "UPDATED"])

        apply()

        # Write report
        with report_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["set_name", "num_products", "primary_sku", "primary_product_name", "action"])
            w.writerows(rows)

        self.stdout.write(self.style.SUCCESS("Armour set build complete."))
        self.stdout.write(f"Armour products scanned: {len(armour_products)}")
        self.stdout.write(f"Sets (min size {min_size}): {len(groups)}")
        self.stdout.write(f"Groups created: {created}")
        self.stdout.write(f"Groups updated: {updated}")
        self.stdout.write(f"Report written: {report_path}")
