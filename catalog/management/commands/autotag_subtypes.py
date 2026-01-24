import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Product


def text_blob(p: Product) -> str:
    parts = [
        p.name or "",
        p.short_description or "",
        p.description or "",
    ]
    s = " ".join(parts).lower()
    s = s.replace("’", "'")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def armour_material_from_text(s: str) -> str:
    # Heuristic: plate if metal keywords, cloth if robe/hood/etc, leather if leather/hide/etc
    plate_kw = ["plate", "armor", "armour", "mail", "chain", "iron", "steel", "knight", "gauntlets", "greaves", "helm", "helmet"]
    cloth_kw = ["robe", "hood", "hat", "cowl", "mantle", "cloth", "silk", "tunic", "gown"]
    leather_kw = ["leather", "hide", "pelt", "fur", "bandit", "boots", "gloves"]

    if any(k in s for k in plate_kw):
        return Product.Subtype.PLATE
    if any(k in s for k in cloth_kw):
        return Product.Subtype.CLOTH
    if any(k in s for k in leather_kw):
        return Product.Subtype.LEATHER
    return Product.Subtype.OTHER


def weapon_type_from_text(s: str) -> str:
    # Order matters: check more specific patterns first
    if "staff" in s or "glintstone staff" in s:
        return Product.Subtype.STAFF
    if "bow" in s or "longbow" in s or "shortbow" in s:
        return Product.Subtype.BOW
    if "dagger" in s or "knife" in s:
        return Product.Subtype.DAGGER
    if "whip" in s:
        return Product.Subtype.WHIP
    if "hammer" in s or "mace" in s or "club" in s:
        return Product.Subtype.HAMMER
    if "axe" in s:
        return Product.Subtype.AXE
    if any(k in s for k in ["spear", "halberd", "glaive", "pike", "lance"]):
        return Product.Subtype.POLEARM
    if any(k in s for k in ["sword", "blade", "katana", "greatsword", "rapier", "scimitar"]):
        return Product.Subtype.SWORD
    if any(k in s for k in ["fist", "claw", "gauntlet weapon"]):
        return Product.Subtype.FIST

    return Product.Subtype.OTHER


def spell_school_from_text(s: str) -> str:
    # Spell classification by lore keywords
    sorcery_kw = [
        "sorcery", "glintstone", "carian", "moon", "primeval", "comet", "gravity",
        "crystal", "academy", "lucaria",
    ]
    incant_kw = [
        "incantation", "prayer", "faith", "two fingers", "golden order", "dragon communion",
        "flame", "fire monk", "black flame", "bestial", "lightning",
    ]

    if any(k in s for k in incant_kw):
        return Product.Subtype.INCANTATION
    if any(k in s for k in sorcery_kw):
        return Product.Subtype.SORCERY

    # fallback
    return Product.Subtype.OTHER


class Command(BaseCommand):
    help = "Auto-tag Product.subtype using keyword rules based on category and lore text."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing.")
        parser.add_argument(
            "--only-empty",
            action="store_true",
            help="Only tag products whose subtype is currently 'other'.",
        )
        parser.add_argument(
            "--report",
            default="reports/subtype_autotag_report.csv",
            help="CSV report output path.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit number of products processed (testing).",
        )

    def handle(self, *args, **opts):
        dry_run = bool(opts["dry_run"])
        only_empty = bool(opts["only_empty"])
        report_path = Path(opts["report"])
        limit = int(opts["limit"])

        qs = Product.objects.all().order_by("id")
        if only_empty:
            qs = qs.filter(subtype=Product.Subtype.OTHER)
        if limit:
            qs = qs[:limit]

        report_path.parent.mkdir(parents=True, exist_ok=True)

        rows = []
        changed = 0
        unchanged = 0

        ctx = transaction.atomic() if not dry_run else nullcontext()
        with ctx:
            for p in qs:
                s = text_blob(p)

                if p.category == Product.Category.ARMOUR:
                    new = armour_material_from_text(s)
                elif p.category == Product.Category.WEAPON or p.category == Product.Category.SHIELD:
                    new = weapon_type_from_text(s)
                elif p.category == Product.Category.SPELL:
                    new = spell_school_from_text(s)
                else:
                    new = Product.Subtype.OTHER

                action = "UNCHANGED"
                if new != p.subtype:
                    action = "UPDATED"
                    changed += 1
                    if not dry_run:
                        p.subtype = new
                        p.save(update_fields=["subtype"])
                else:
                    unchanged += 1

                rows.append([p.sku, p.name, p.category, p.subtype, new, action])

        with report_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["sku", "name", "category", "old_subtype", "new_subtype", "action"])
            w.writerows(rows)

        self.stdout.write(self.style.SUCCESS("Subtype autotag complete."))
        self.stdout.write(f"Dry run: {dry_run}")
        self.stdout.write(f"Processed: {len(rows)}")
        self.stdout.write(f"Updated: {changed}")
        self.stdout.write(f"Unchanged: {unchanged}")
        self.stdout.write(f"Report: {report_path}")


try:
    from contextlib import nullcontext  # type: ignore
except ImportError:  # pragma: no cover
    class nullcontext:
        def __enter__(self): return None
        def __exit__(self, *exc): return False
