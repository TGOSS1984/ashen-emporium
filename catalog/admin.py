from django.contrib import admin
from .models import Product, Asset, ProductImage


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


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "rarity", "price_pence", "stock_qty", "is_active", "updated_at")
    list_filter = ("category", "rarity", "is_active")
    search_fields = ("sku", "name")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)
    inlines = [ProductImageInline]


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("admin_thumb", "asset_id", "title", "source", "created_at")
    search_fields = ("asset_id", "title", "source")
    ordering = ("-created_at",)

