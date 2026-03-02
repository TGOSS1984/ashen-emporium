from decimal import Decimal

from django.contrib import admin, messages
from django.db.models import Sum
from django.utils import timezone

from .models import Order, OrderItem


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
    )
    # Keep your existing filters, add ops filter
    list_filter = ("status", PaidFulfilmentFilter, "created_at")
    search_fields = ("id", "user__username", "user__email")
    actions = [mark_fulfilled]
    ordering = ("-id",)

    def changelist_view(self, request, extra_context=None):
        """
        Adds lightweight KPIs to the changelist template context.
        Safe even if you haven't added the template override yet.
        """
        extra_context = extra_context or {}
        qs = self.get_queryset(request)

        now = timezone.now()
        start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_7d = now - timezone.timedelta(days=7)

        orders_today = qs.filter(created_at__gte=start_today).count()
        orders_7d = qs.filter(created_at__gte=start_7d).count()

        # Paid but not fulfilled (uses fulfilled_at if it exists, else just PAID)
        has_fulfilled_at = hasattr(Order, "fulfilled_at")
        paid_unfulfilled_qs = qs.filter(status=Order.Status.PAID)
        if has_fulfilled_at:
            paid_unfulfilled_qs = paid_unfulfilled_qs.filter(fulfilled_at__isnull=True)
        paid_unfulfilled = paid_unfulfilled_qs.count()

        # Revenue last 7 days (uses your existing total_gbp property/field if it's aggregatable)
        # If total_gbp is a @property, Sum won't work. We'll try common DB fields first.
        revenue_7d = None
        revenue_field = None

        for candidate in ("grand_total_gbp", "total_gbp", "total", "order_total", "total_amount", "total_pence"):
            if hasattr(Order, candidate):
                revenue_field = candidate
                break

        if revenue_field:
            try:
                agg = qs.filter(created_at__gte=start_7d, status__in=[Order.Status.PAID, Order.Status.FULFILLED]).aggregate(
                    s=Sum(revenue_field)
                )
                revenue_7d = agg["s"] or Decimal("0.00")
            except Exception:
                # If it's not a real DB field (e.g., @property), don't crash admin
                revenue_7d = None
                revenue_field = None

        extra_context["ops_kpis"] = {
            "orders_today": orders_today,
            "orders_7d": orders_7d,
            "paid_unfulfilled": paid_unfulfilled,
            "revenue_7d": revenue_7d,
            "revenue_field": revenue_field,
        }

        return super().changelist_view(request, extra_context=extra_context)