import stripe

from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, IntegrityError
from django.db.models import Sum, F
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from orders.models import Order
from catalog.models import Product
from orders.emails import send_order_paid_email

from .models import StripeEvent


stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def start_checkout(request, order_id: int):
    """
    Create a Stripe Checkout Session for an order (must be PLACED and not already PAID).
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status == Order.Status.PAID:
        messages.info(request, "This order is already paid.")
        return redirect("order_confirmation", order_id=order.id)

    if not settings.STRIPE_SECRET_KEY:
        messages.error(request, "Stripe is not configured (missing secret key).")
        return redirect("order_confirmation", order_id=order.id)

    reset = request.GET.get("reset") == "1"

    # Resume existing Stripe session if one already exists (unless reset requested)
    if order.status == Order.Status.PLACED and order.stripe_session_url and not reset:
        return redirect(order.stripe_session_url)

    success_url = request.build_absolute_uri(reverse("payment_success")) + f"?order_id={order.id}"
    cancel_url = request.build_absolute_uri(reverse("payment_cancel")) + f"?order_id={order.id}"

    # Build line items from order snapshot
    line_items = []
    for item in order.items.all():
        line_items.append(
            {
                "price_data": {
                    "currency": "gbp",
                    "product_data": {"name": item.product_name},
                    "unit_amount": item.unit_price_pence,
                },
                "quantity": item.qty,
            }
        )

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=line_items,
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=str(order.id),
        metadata={"order_id": str(order.id)},
    )

    order.stripe_session_id = session.id
    order.stripe_payment_intent_id = session.payment_intent or ""
    order.stripe_session_url = session.url or ""
    order.save(update_fields=["stripe_session_id", "stripe_payment_intent_id", "stripe_session_url"])

    return redirect(session.url)


@login_required
def payment_success(request):
    """
    Customer landed here after paying. Webhook will set PAID (source of truth).
    """
    order_id = request.GET.get("order_id")
    order = None
    if order_id:
        order = Order.objects.filter(id=order_id, user=request.user).first()

    return render(request, "payments/success.html", {"order": order})


@login_required
def payment_cancel(request):
    order_id = request.GET.get("order_id")
    order = None
    if order_id:
        order = Order.objects.filter(id=order_id, user=request.user).first()
    return render(request, "payments/cancel.html", {"order": order})


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if not webhook_secret:
        return HttpResponseBadRequest("Webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        return HttpResponseBadRequest("Invalid payload")
    except stripe.error.SignatureVerificationError:
        return HttpResponseBadRequest("Invalid signature")

    # Only handle the event we care about
    if event["type"] != "checkout.session.completed":
        return HttpResponse(status=200)

    event_id = event.get("id", "")
    session = event["data"]["object"]
    session_id = session.get("id")
    order_id = session.get("metadata", {}).get("order_id")

    # Convert Stripe created timestamp to timezone-aware datetime (optional)
    stripe_created_dt = None
    if event.get("created"):
        stripe_created_dt = timezone.datetime.fromtimestamp(
            int(event["created"]),
            tz=timezone.utc
        )

    with transaction.atomic():
        # 1) Idempotency gate: store event id once, no-op if already processed
        try:
            StripeEvent.objects.create(
                event_id=event_id,
                event_type=event["type"],
                livemode=bool(event.get("livemode", False)),
                stripe_created=stripe_created_dt,
            )
        except IntegrityError:
            # This Stripe event was already processed
            return HttpResponse(status=200)

        order_qs = Order.objects.select_for_update()

        order = None
        if order_id:
            order = order_qs.filter(id=order_id).first()

        if order is None and session_id:
            order = order_qs.filter(stripe_session_id=session_id).first()

        if not order:
            # Keep StripeEvent record so we don't spin on retries for unknown orders
            return HttpResponse(status=200)

        just_marked_paid = False

        if order.status != Order.Status.PAID:
            order.status = Order.Status.PAID
            order.stripe_session_id = session.get("id", order.stripe_session_id)
            order.stripe_payment_intent_id = session.get("payment_intent", order.stripe_payment_intent_id) or ""
            order.save(update_fields=["status", "stripe_session_id", "stripe_payment_intent_id"])
            just_marked_paid = True

        # 2) Stock decrement only when we actually transitioned to PAID
        if just_marked_paid:
            for item in order.items.all():
                # Use SKU snapshot from OrderItem to find Product
                # (If SKU can be null, guard it)
                if not item.sku:
                    continue

                # Atomic decrement in DB
                updated = Product.objects.filter(sku=item.sku, stock_qty__gt=0).update(
                    stock_qty=F("stock_qty") - item.qty
                )

                # Optional clamp if qty > stock: prevent negative in rare cases
                # (You can tighten this later to enforce "no oversell" rules)
                if updated:
                    Product.objects.filter(sku=item.sku, stock_qty__lt=0).update(stock_qty=0)

        # 3) Email: mark timestamp in DB, send after commit to avoid “email sent but DB rolled back”
        send_email = False
        if order.paid_email_sent_at is None:
            order.paid_email_sent_at = timezone.now()
            order.save(update_fields=["paid_email_sent_at"])
            send_email = True

        if send_email:
            order_id_to_email = order.id

            def _send():
                # Refetch in case template uses related objects
                o = Order.objects.get(id=order_id_to_email)
                send_order_paid_email(o)

            transaction.on_commit(_send)

    return HttpResponse(status=200)