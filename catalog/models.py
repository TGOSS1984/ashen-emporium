from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Product(models.Model):
    class Category(models.TextChoices):
        WEAPON = "weapon", "Weapon"
        SHIELD = "shield", "Shield"
        ARMOUR = "armour", "Armour"
        RELIC = "relic", "Relic"
        CONSUMABLE = "consumable", "Consumable"

    class Rarity(models.TextChoices):
        COMMON = "common", "Common"
        RARE = "rare", "Rare"
        MYTHIC = "mythic", "Mythic"
        RELIC = "relic", "Relic"

    sku = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True, blank=True)

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.WEAPON,
    )
    rarity = models.CharField(
        max_length=20,
        choices=Rarity.choices,
        default=Rarity.COMMON,
    )

    # Store money as integer minor units (pence) to avoid float issues.
    price_pence = models.PositiveIntegerField(help_text="Price in pence (e.g. 1299 = £12.99)")
    stock_qty = models.PositiveIntegerField(default=0)

    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.sku})"

    @property
    def price_gbp(self) -> str:
        pounds = self.price_pence / 100
        return f"£{pounds:,.2f}"

    @property
    def in_stock(self) -> bool:
        return self.stock_qty > 0

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            i = 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)
