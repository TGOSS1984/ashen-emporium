# payments/admin.py
from django.contrib import admin
from .models import StripeEvent


@admin.register(StripeEvent)
class StripeEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "event_id", "livemode", "stripe_created", "created_at")
    search_fields = ("event_id", "event_type")
    list_filter = ("event_type", "livemode", "created_at")
    ordering = ("-created_at",)