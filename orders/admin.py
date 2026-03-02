from decimal import Decimal

from django.contrib import admin, messages
from django.db.models import Sum
from django.utils import timezone

from .models import Order, OrderItem

from django.urls import reverse
from django.utils.http import urlencode


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "sku", "unit_price_pence", "qty", "line_total_pence")


class PaidFulfilmentFilter(admin.SimpleListFilter):
    """
    Adds an ops-friendly filter:
      - Paid, not fulfilled
      - Fulfilled
      - Unpaid
    Falls back gracefully if fulfilled_at doesn't exist on the Order model.
    """
    title = "Paid / Fulfilment"
    parameter_name = "fulfilment"

    def lookups(self, request, model_admin):
        return (
            ("paid_unfulfilled", "Paid, not fulfilled"),
            ("fulfilled", "Fulfilled"),
            ("unpaid", "Unpaid / not paid"),
        )

    def queryset(self, request, queryset):
        val = self.value()
        if not val:
            return queryset

        has_fulfilled_at = hasattr(Order, "fulfilled_at")

        if val == "paid_unfulfilled":
            qs = queryset.filter(status=Order.Status.PAID)
            if has_fulfilled_at:
                qs = qs.filter(fulfilled_at__isnull=True)
            return qs

        if val == "fulfilled":
            return queryset.filter(status=Order.Status.FULFILLED)

        if val == "unpaid":
            # anything not paid or fulfilled
            return queryset.exclude(status__in=[Order.Status.PAID, Order.Status.FULFILLED])

        return queryset


@admin.action(description="Mark selected orders as fulfilled")
def mark_fulfilled(modeladmin, request, queryset):
    """
    Marks ONLY paid orders as fulfilled (prevents accidental fulfilment of unpaid orders).
    If fulfilled_at exists, sets it for newly-fulfilled orders.
    """
    now = timezone.now()
    has_fulfilled_at = hasattr(Order, "fulfilled_at")

    # Only eligible: PAID (and not already fulfilled)
    eligible = queryset.filter(status=Order.Status.PAID)

    if has_fulfilled_at:
        # only mark those without a fulfilled timestamp to avoid "re-fulfilling"
        eligible = eligible.filter(fulfilled_at__isnull=True)

    if not eligible.exists():
        modeladmin.message_user(
            request,
            "No eligible orders selected (only PAID orders can be marked as fulfilled).",
            level=messages.WARNING,
        )
        return

    update_fields = {"status": Order.Status.FULFILLED}
    if has_fulfilled_at:
        update_fields["fulfilled_at"] = now

    updated = eligible.update(**update_fields)

    modeladmin.message_user(
        request,
        f"Marked {updated} order(s) as fulfilled.",
        level=messages.SUCCESS,
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]

    list_display = (
        "id",
        "user",
        "status",
        "total_gbp",
        "created_at",
        "refunded_at",
    )
    # Keep your existing filters, add ops filter
    list_filter = ("status", PaidFulfilmentFilter, "created_at")
    search_fields = ("id", "user__username", "user__email")
    actions = [mark_fulfilled]
    ordering = ("-id",)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = self.get_queryset(request)

        now = timezone.now()
        start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_7d = now - timezone.timedelta(days=7)
        start_24h = now - timezone.timedelta(hours=24)

        orders_today = qs.filter(created_at__gte=start_today).count()
        orders_7d = qs.filter(created_at__gte=start_7d).count()

        has_fulfilled_at = hasattr(Order, "fulfilled_at")
        paid_unfulfilled_qs = qs.filter(status=Order.Status.PAID)
        if has_fulfilled_at:
            paid_unfulfilled_qs = paid_unfulfilled_qs.filter(fulfilled_at__isnull=True)
        paid_unfulfilled = paid_unfulfilled_qs.count()

        # Revenue: PAID + FULFILLED only
        paid_like = [Order.Status.PAID, Order.Status.FULFILLED]
        revenue_7d_pence = (
            qs.filter(created_at__gte=start_7d, status__in=paid_like)
            .aggregate(s=Sum("total_pence"))
            .get("s")
            or 0
        )
        revenue_7d = Decimal(revenue_7d_pence) / Decimal("100")

        # Refunds: count + amount (if you keep refunded orders around)
        refunded_status = getattr(Order.Status, "REFUNDED", None)
        refunded_7d = 0
        refunded_7d_amount = Decimal("0.00")
        if refunded_status:
            refunded_7d_qs = qs.filter(created_at__gte=start_7d, status=refunded_status)
            refunded_7d = refunded_7d_qs.count()
            refunded_7d_pence = refunded_7d_qs.aggregate(s=Sum("total_pence")).get("s") or 0
            refunded_7d_amount = Decimal(refunded_7d_pence) / Decimal("100")

        net_revenue_7d = revenue_7d - refunded_7d_amount

        # Quick links (safe even if models/admin URLs change slightly)
        low_stock_url = None
        try:
            low_stock_url = reverse("admin:catalog_product_changelist") + "?" + urlencode({"stock_qty__lte": 3})
        except Exception:
            pass

        stripe_events_url = None
        try:
            stripe_events_url = reverse("admin:payments_stripeevent_changelist")
        except Exception:
            pass

        extra_context["ops_kpis"] = {
            "orders_today": orders_today,
            "orders_7d": orders_7d,
            "paid_unfulfilled": paid_unfulfilled,
            "revenue_7d": revenue_7d,
            "refunded_7d": refunded_7d,
            "refunded_7d_amount": refunded_7d_amount,
            "net_revenue_7d": net_revenue_7d,
            "low_stock_url": low_stock_url,
            "stripe_events_url": stripe_events_url,
        }

        return super().changelist_view(request, extra_context=extra_context)