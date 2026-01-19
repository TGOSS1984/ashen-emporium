from django.core.management.base import BaseCommand
from django.utils.text import slugify
from catalog.models import Product
import random


class Command(BaseCommand):
    help = "Seed demo products for Ashen Emporium"

    def handle(self, *args, **options):
        if Product.objects.exists():
            self.stdout.write(self.style.WARNING("Products already exist — skipping seed."))
            return

        products = [
            # Weapons
            ("Ashen Longsword", "WEAPON", "RARE", 2499, 5),
            ("Cinderbrand Dagger", "WEAPON", "UNCOMMON", 1599, 8),
            ("Gravewarden Halberd", "WEAPON", "EPIC", 3999, 2),

            # Shields
            ("Black Iron Kite Shield", "SHIELD", "COMMON", 1299, 10),
            ("Embercrest Bulwark", "SHIELD", "RARE", 2799, 4),

            # Armour
            ("Knight of Cinder Helm", "ARMOUR", "RARE", 1899, 6),
            ("Ashbound Plate Cuirass", "ARMOUR", "EPIC", 4499, 2),

            # Consumables
            ("Ember Flask", "CONSUMABLE", "COMMON", 499, 25),
            ("Charred Resin", "CONSUMABLE", "UNCOMMON", 799, 15),

            # Relics
            ("Ring of Smouldering Will", "RELIC", "RARE", 2999, 3),
            ("Ashen Sigil of Binding", "RELIC", "EPIC", 4999, 1),

            # Spells
            ("Pyre Lance Scroll", "SPELL", "RARE", 2199, 5),
            ("Cindersurge Manuscript", "SPELL", "EPIC", 3599, 2),
        ]

        created = 0

        for name, category, rarity, price_pence, stock in products:
            product = Product.objects.create(
                name=name,
                slug=slugify(name),
                sku=f"DEMO-{slugify(name).upper()}",
                category=category,
                rarity=rarity,
                price_pence=price_pence,
                stock_qty=stock,
                short_description="A relic forged in ash and memory.",
                description=(
                    "Forged in the dying embers of a forgotten age, this item "
                    "bears the scars of countless battles. Few remain who "
                    "remember its true purpose."
                ),
                is_active=True,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} demo products."))
