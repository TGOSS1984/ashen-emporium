# payments/admin.py

from django.contrib import admin
from .models import StripeEvent


@admin.register(StripeEvent)
class StripeEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "event_id",
        "stripe_created",
        "livemode",
        "created_at",
    )

    list_filter = (
        "event_type",
        "livemode",
    )

    search_fields = (
        "event_id",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "event_id",
        "event_type",
        "stripe_created",
        "livemode",
        "created_at",
    )

    # Prevent manual tampering
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False