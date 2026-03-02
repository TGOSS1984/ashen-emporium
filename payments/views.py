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

    event_type = event["type"]

    REFUND_EVENTS = ("charge.refunded", "charge.refund.updated", "refund.created", "refund.updated")

    if event_type not in ("checkout.session.completed", *REFUND_EVENTS):
        return HttpResponse(status=200)

    event_id = event.get("id", "")
    if not event_id:
        return HttpResponseBadRequest("Missing Stripe event id")

    stripe_created_dt = None
    if event.get("created"):
        stripe_created_dt = timezone.datetime.fromtimestamp(int(event["created"]), tz=timezone.utc)

    with transaction.atomic():
        # Idempotency gate
        try:
            StripeEvent.objects.create(
                event_id=event_id,
                event_type=event_type,
                livemode=bool(event.get("livemode", False)),
                stripe_created=stripe_created_dt,
            )
        except IntegrityError:
            return HttpResponse(status=200)

        # -----------------------------
        # A) Checkout completed (mark paid + decrement stock + paid email)
        # -----------------------------
        if event_type == "checkout.session.completed":
            session = event["data"]["object"]
            session_id = session.get("id")
            order_id = session.get("metadata", {}).get("order_id")

            order_qs = Order.objects.select_for_update()

            order = None
            if order_id:
                order = order_qs.filter(id=order_id).first()

            if order is None and session_id:
                order = order_qs.filter(stripe_session_id=session_id).first()

            if not order:
                return HttpResponse(status=200)

            just_marked_paid = False
            if order.status != Order.Status.PAID:
                order.status = Order.Status.PAID
                order.stripe_session_id = session.get("id", order.stripe_session_id)
                order.stripe_payment_intent_id = session.get("payment_intent", order.stripe_payment_intent_id) or ""
                order.save(update_fields=["status", "stripe_session_id", "stripe_payment_intent_id"])
                just_marked_paid = True

            if just_marked_paid:
                for item in order.items.all():
                    if not item.sku:
                        continue
                    updated = Product.objects.filter(sku=item.sku, stock_qty__gt=0).update(
                        stock_qty=F("stock_qty") - item.qty
                    )
                    if updated:
                        Product.objects.filter(sku=item.sku, stock_qty__lt=0).update(stock_qty=0)

            # Paid email (only for checkout completion)
            send_email = False
            if order.paid_email_sent_at is None:
                order.paid_email_sent_at = timezone.now()
                order.save(update_fields=["paid_email_sent_at"])
                send_email = True

            if send_email:
                order_id_to_email = order.id

                def _send():
                    o = Order.objects.get(id=order_id_to_email)
                    send_order_paid_email(o)

                transaction.on_commit(_send)

            return HttpResponse(status=200)

        # -----------------------------
        # B) Refund (restore stock + mark refunded)
        # -----------------------------
        if event_type in REFUND_EVENTS:
            obj = event["data"]["object"]

            # refund.* and charge.refund.updated give you a Refund object
            payment_intent_id = obj.get("payment_intent")

            # charge.refunded gives you a Charge object
            if not payment_intent_id and obj.get("object") == "charge":
                payment_intent_id = obj.get("payment_intent")

            if not payment_intent_id:
                return HttpResponse(status=200)

            order = Order.objects.select_for_update().filter(
                stripe_payment_intent_id=payment_intent_id
            ).first()

            if not order:
                return HttpResponse(status=200)

            if order.status == Order.Status.REFUNDED:
                return HttpResponse(status=200)

            for item in order.items.all():
                if not item.sku:
                    continue
                Product.objects.filter(sku=item.sku).update(
                    stock_qty=F("stock_qty") + item.qty
                )

            order.status = Order.Status.REFUNDED
            order.refunded_at = timezone.now()
            order.save(update_fields=["status", "refunded_at"])

            return HttpResponse(status=200)

    return HttpResponse(status=200)