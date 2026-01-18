from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "sku", "unit_price_pence", "qty", "line_total_pence")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "status", "total_pence", "created_at")
    list_filter = ("status",)
    search_fields = ("email", "id")
    inlines = [OrderItemInline]
