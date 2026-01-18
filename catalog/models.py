from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from django.core.validators import FileExtensionValidator
from django.utils.html import format_html



class Product(models.Model):
    class Category(models.TextChoices):
        WEAPON = "weapon", "Weapon"
        SHIELD = "shield", "Shield"
        ARMOUR = "armour", "Armour"
        RELIC = "relic", "Relic"
        CONSUMABLE = "consumable", "Consumable"
        SPELL = "spell", "Spell"

    class Rarity(models.TextChoices):
        COMMON = "common", "Common"
        RARE = "rare", "Rare"
        MYTHIC = "mythic", "Mythic"
        RELIC = "relic", "Relic"

    sku = models.CharField(max_length=64, unique=True)
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

    def primary_image(self):
        primary = self.images.filter(is_primary=True).select_related("asset").first()
        if primary:
            return primary.asset.image
        first = self.images.select_related("asset").first()
        return first.asset.image if first else None


class Asset(models.Model):
    """
    A raw media asset (usually an image) that can later be attached to products.
    This is intentionally separate from Product so we can import an image library first.
    """
    asset_id = models.CharField(max_length=64, unique=True, help_text="Stable ID (e.g. filename stem or hash)")
    image = models.ImageField(
        upload_to="assets/",
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"])],
    )

    title = models.CharField(max_length=140, blank=True)
    source = models.CharField(max_length=140, blank=True, help_text="Optional: where this asset came from")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title or self.asset_id

    def admin_thumb(self) -> str:
        if not self.image:
            return "-"
        return format_html(
            '<img src="{}" style="height:50px;width:auto;border-radius:6px;border:1px solid #1f2933;" />',
            self.image.url,
        )

    admin_thumb.short_description = "Preview"


class ProductImage(models.Model):
    """
    Join table: a product can have multiple images; an asset can be reused.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="product_links")

    alt_text = models.CharField(max_length=140, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["product", "asset"], name="uniq_product_asset"),
        ]

    def __str__(self) -> str:
        return f"{self.product.sku} → {self.asset.asset_id}"
    
    def save(self, *args, **kwargs):
        """
            Ensure only one primary image per product.
            If this row is set primary, unset all other primary images for the same product.
        """
        super().save(*args, **kwargs)

        if self.is_primary:
            ProductImage.objects.filter(product=self.product).exclude(pk=self.pk).update(is_primary=False)


