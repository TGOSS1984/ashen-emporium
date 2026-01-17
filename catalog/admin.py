from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "rarity", "price_pence", "stock_qty", "is_active", "updated_at")
    list_filter = ("category", "rarity", "is_active")
    search_fields = ("sku", "name")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)

