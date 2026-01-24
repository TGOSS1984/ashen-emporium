import re
from datetime import datetime

from django import forms
from django.contrib.admin.helpers import ActionForm

from django.contrib import admin, messages
from django.db import transaction

from django.contrib import admin
from django.db.models import Q

from .models import Product, Asset, ProductImage, ProductGroup

class HasLoreFilter(admin.SimpleListFilter):
    title = "lore"
    parameter_name = "has_lore"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Has lore"),
            ("no", "Missing lore"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.exclude(Q(description="") & Q(short_description=""))
        if self.value() == "no":
            return queryset.filter(Q(description="") & Q(short_description=""))
        return queryset
class StockFilter(admin.SimpleListFilter):
    title = "stock"
    parameter_name = "stock_state"

    def lookups(self, request, model_admin):
        return (
            ("in", "In stock"),
            ("out", "Out of stock"),
        )

    def queryset(self, request, queryset):
        if self.value() == "in":
            return queryset.filter(stock_qty__gt=0)
        if self.value() == "out":
            return queryset.filter(stock_qty=0)
        return queryset
   
class ProductActionForm(ActionForm):
    stock_value = forms.IntegerField(required=False, min_value=0, label="Stock")
    price_pence = forms.IntegerField(required=False, min_value=0, label="Price (pence)")


def folder_to_category(source: str) -> str:
    """
    Asset.source looks like 'external-library:weapons'.
    Map that folder name to Product.Category values.
    """
    # Default
    category = Product.Category.RELIC

    if not source:
        return category

    folder = source.split(":")[-1].strip().lower()

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
    return mapping.get(folder, category)


def make_sku(category: str, asset_id: str) -> str:
    """
    Generate a stable-ish SKU:
    ASH-<CAT>-<ASSET>
    Example: ASH-WEP-graveglass-sabre-01
    """
    cat_map = {
        Product.Category.WEAPON: "WEP",
        Product.Category.SHIELD: "SHD",
        Product.Category.ARMOUR: "ARM",
        Product.Category.RELIC: "REL",
        Product.Category.CONSUMABLE: "CON",
        Product.Category.SPELL: "SPL",
    }
    cat_code = cat_map.get(category, "GEN")

    # Keep SKUs short-ish and clean
    cleaned = re.sub(r"[^a-z0-9\-]+", "", (asset_id or "").lower())[:18].strip("-")
    stamp = datetime.utcnow().strftime("%H%M%S")  # avoid collisions if needed
    return f"ASH-{cat_code}-{cleaned}-{stamp}"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    autocomplete_fields = ["asset"]
    fields = ("asset", "preview", "alt_text", "sort_order", "is_primary")
    readonly_fields = ("preview",)

    def preview(self, obj):
        if obj.asset and obj.asset.image:
            return obj.asset.admin_thumb()
        return "-"

    preview.short_description = "Preview"


@admin.action(description="Create draft product(s) from selected asset(s)")
def create_products_from_assets(modeladmin, request, queryset):
    """
    For each selected Asset:
    - create a Product (draft defaults)
    - link the asset as primary ProductImage
    """
    created_count = 0
    skipped_count = 0

    with transaction.atomic():
        for asset in queryset:
            # Basic defaults
            category = folder_to_category(asset.source)
            name = asset.title or asset.asset_id.replace("-", " ").replace("_", " ").title()

            # Create product
            sku = make_sku(category, asset.asset_id)

            product = Product.objects.create(
                sku=sku,
                name=name,
                category=category,
                rarity=Product.Rarity.COMMON,
                price_pence=999,     # placeholder (£9.99) - edit later
                stock_qty=0,         # start at 0 until you choose stock policy
                short_description=asset.title[:255] if asset.title else "",
                is_active=False,     # draft by default; publish when ready
            )

            # Link image as primary
            ProductImage.objects.create(
                product=product,
                asset=asset,
                alt_text=name,
                sort_order=0,
                is_primary=True,
            )

            created_count += 1

    messages.success(request, f"Created {created_count} draft product(s) from selected asset(s).")
    if skipped_count:
        messages.warning(request, f"Skipped {skipped_count} asset(s).")

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("admin_thumb", "asset_id", "title", "source", "created_at")
    search_fields = ("asset_id", "title", "source")
    ordering = ("-created_at",)
    actions = [create_products_from_assets]

@admin.action(description="Publish selected products")
def publish_products(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f"Published {updated} product(s).")


@admin.action(description="Unpublish selected products")
def unpublish_products(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f"Unpublished {updated} product(s).")


@admin.action(description="Set stock quantity for selected products")
def set_stock(modeladmin, request, queryset):
    stock_raw = request.POST.get("stock_value")
    try:
        stock = int(stock_raw)
    except (TypeError, ValueError):
        modeladmin.message_user(request, "Enter a Stock value (integer) above, then run the action.", level="ERROR")
        return

    updated = queryset.update(stock_qty=stock)
    modeladmin.message_user(request, f"Set stock to {stock} for {updated} product(s).")



@admin.action(description="Set price (pence) for selected products")
def set_price_pence(modeladmin, request, queryset):
    price_raw = request.POST.get("price_pence")
    try:
        price = int(price_raw)
    except (TypeError, ValueError):
        modeladmin.message_user(request, "Enter a Price (pence) value above, then run the action.", level="ERROR")
        return

    updated = queryset.update(price_pence=price)
    modeladmin.message_user(request, f"Set price to {price}p for {updated} product(s).")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "subtype", "rarity", "price_pence", "stock_qty", "is_active", "updated_at")
    list_filter = ("category", "rarity", "subtype", "is_active", StockFilter, HasLoreFilter)
    search_fields = ("sku", "name")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)
    inlines = [ProductImageInline]
    actions = [publish_products, unpublish_products, set_stock, set_price_pence]
    action_form = ProductActionForm

@admin.register(ProductGroup)
class ProductGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "group_type", "category", "primary_product")
    list_filter = ("group_type", "category")
    search_fields = ("name",)
    filter_horizontal = ("products",)
