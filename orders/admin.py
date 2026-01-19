from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "sku", "unit_price_pence", "qty", "line_total_pence")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "status",
        "total_gbp",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("id", "user__username", "user__email")

@admin.action(description="Mark selected orders as fulfilled")
def mark_fulfilled(modeladmin, request, queryset):
    queryset.filter(status=Order.Status.PAID).update(status=Order.Status.FULFILLED)


